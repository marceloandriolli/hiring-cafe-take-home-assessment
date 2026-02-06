#!/usr/bin/env python3
"""
Async incremental scraper combining concurrent scraping with database tracking.
Best of both worlds: Phase 2 (incremental) + Phase 3 (async).
"""

import asyncio
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

from async_scraper import AsyncAvatureScraper
from database import JobDatabase


class AsyncIncrementalScraper:
    """Async scraper with incremental database tracking and smart stopping."""

    def __init__(self, db_path: str = "data/jobs.db",
                 use_url_detector=True,
                 smart_stop_pages: int = 5,
                 max_concurrent_sites: int = 5,
                 max_concurrent_pages: int = 3,
                 rate_limit_delay: float = 0.5):
        """Initialize async incremental scraper.

        Args:
            db_path: Path to SQLite database
            use_url_detector: Use URL detector for pattern detection
            smart_stop_pages: Stop after N consecutive pages with no new jobs
            max_concurrent_sites: Maximum sites to scrape concurrently
            max_concurrent_pages: Maximum pages per site concurrently
            rate_limit_delay: Delay between requests in seconds
        """
        self.db = JobDatabase(db_path)
        self.smart_stop_pages = smart_stop_pages

        # Async scraper settings
        self.use_url_detector = use_url_detector
        self.max_concurrent_sites = max_concurrent_sites
        self.max_concurrent_pages = max_concurrent_pages
        self.rate_limit_delay = rate_limit_delay

        # Async scraper (created in async context)
        self.scraper = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Create async scraper
        self.scraper = AsyncAvatureScraper(
            use_url_detector=self.use_url_detector,
            max_concurrent_sites=self.max_concurrent_sites,
            max_concurrent_pages=self.max_concurrent_pages,
            rate_limit_delay=self.rate_limit_delay
        )
        await self.scraper.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.scraper:
            await self.scraper.__aexit__(exc_type, exc_val, exc_tb)
        self.db.close()

    async def scrape_site_incremental(self, base_url: str) -> Dict:
        """Scrape a site with smart stopping and database tracking.

        Args:
            base_url: Base URL of the site

        Returns:
            Statistics dictionary
        """
        print(f"\nScraping: {base_url}")

        site_stats = {
            'url': base_url,
            'jobs_found': 0,
            'jobs_new': 0,
            'jobs_updated': 0,
            'jobs_unchanged': 0,
            'jobs_deactivated': 0,
            'success': False,
            'error': None,
            'stopped_early': False
        }

        try:
            # Detect URL pattern
            if self.scraper.use_url_detector and self.scraper.url_detector:
                pattern = self.scraper.detect_pattern(base_url)

                if pattern is None:
                    site_stats['error'] = "No compatible URL pattern found"
                    print(f"  ✗ {site_stats['error']}")
                    return site_stats

                search_url = f"{base_url}{pattern}"
            else:
                search_url = f"{base_url}/SearchJobs"

            # Scrape with smart stopping
            jobs, stopped_early = await self.scrape_with_smart_stop(
                search_url, base_url
            )

            site_stats['jobs_found'] = len(jobs)
            site_stats['stopped_early'] = stopped_early
            site_stats['success'] = True

            # Process jobs through database
            active_urls = []
            for job in jobs:
                action, changed = self.db.upsert_job(job)

                if action == 'new':
                    site_stats['jobs_new'] += 1
                elif action == 'updated':
                    site_stats['jobs_updated'] += 1
                else:
                    site_stats['jobs_unchanged'] += 1

                active_urls.append(job['url'])

            # Mark unseen jobs as inactive
            company = jobs[0]['company'] if jobs else None
            if company:
                deactivated = self.db.mark_inactive_jobs(active_urls, company)
                site_stats['jobs_deactivated'] = deactivated

            # Print summary
            print(f"  ✓ Found {len(jobs)} jobs")
            if site_stats['jobs_new'] > 0:
                print(f"    • {site_stats['jobs_new']} new")
            if site_stats['jobs_updated'] > 0:
                print(f"    • {site_stats['jobs_updated']} updated")
            if site_stats['jobs_unchanged'] > 0:
                print(f"    • {site_stats['jobs_unchanged']} unchanged")
            if site_stats['jobs_deactivated'] > 0:
                print(f"    • {site_stats['jobs_deactivated']} deactivated")
            if stopped_early:
                print(f"    • Stopped early (no new jobs in {self.smart_stop_pages} pages)")

        except Exception as e:
            site_stats['error'] = str(e)
            print(f"  ✗ Error: {e}")

        return site_stats

    async def scrape_with_smart_stop(self, search_url: str,
                                     base_url: str) -> tuple:
        """Scrape pages with smart stopping.

        Args:
            search_url: Search URL
            base_url: Base site URL

        Returns:
            Tuple of (jobs_list, stopped_early_bool)
        """
        all_jobs = []
        page = 1
        pages_without_new = 0
        max_pages = 100

        # Get existing job URLs from database for this company
        company = base_url.split('.')[0].replace('https://', '')
        existing_urls = set()

        try:
            existing_jobs = self.db.get_active_jobs(company=company)
            existing_urls = {job['url'] for job in existing_jobs}
        except:
            pass  # First time scraping this company

        while page <= max_pages:
            # Scrape page
            page_jobs = await self.scraper.scrape_single_page(
                search_url, base_url, page
            )

            if not page_jobs:
                print(f"  Page {page}: No jobs (end)")
                break

            # Check if any jobs are new
            new_jobs_on_page = sum(
                1 for job in page_jobs if job['url'] not in existing_urls
            )

            print(f"  Page {page}: {len(page_jobs)} jobs "
                  f"({new_jobs_on_page} potentially new)")

            all_jobs.extend(page_jobs)

            # Smart stopping logic
            if new_jobs_on_page == 0:
                pages_without_new += 1
                if pages_without_new >= self.smart_stop_pages:
                    return all_jobs, True  # Stopped early
            else:
                pages_without_new = 0
                # Add new URLs to existing set
                for job in page_jobs:
                    existing_urls.add(job['url'])

            page += 1
            await asyncio.sleep(0.3)  # Brief delay between pages

        return all_jobs, False  # Scraped all pages

    async def scrape_all_sites_incremental(self, sites: List[str]) -> Dict:
        """Scrape all sites with incremental updates (concurrent).

        Args:
            sites: List of site URLs

        Returns:
            Overall statistics dictionary
        """
        print("="*80)
        print(f"ASYNC INCREMENTAL SCRAPE: {len(sites)} sites")
        print(f"Concurrency: {self.max_concurrent_sites} sites")
        print(f"Database: {self.db.db_path}")
        print("="*80)

        # Start scrape run
        run_id = self.db.start_scrape_run()

        # Overall stats
        overall_stats = {
            'run_id': run_id,
            'started_at': datetime.now().isoformat(),
            'sites_scraped': 0,
            'sites_succeeded': 0,
            'sites_failed': 0,
            'jobs_found': 0,
            'jobs_new': 0,
            'jobs_updated': 0,
            'jobs_unchanged': 0,
            'jobs_deactivated': 0,
            'site_results': []
        }

        # Create semaphore for concurrent site scraping
        semaphore = asyncio.Semaphore(self.max_concurrent_sites)

        async def scrape_site_with_semaphore(site):
            """Scrape site with concurrency limit."""
            async with semaphore:
                result = await self.scrape_site_incremental(site)
                await asyncio.sleep(self.rate_limit_delay)
                return result

        # Scrape all sites concurrently
        tasks = [scrape_site_with_semaphore(site) for site in sites]
        site_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for site, result in zip(sites, site_results):
            if isinstance(result, Exception):
                overall_stats['site_results'].append({
                    'url': site,
                    'success': False,
                    'error': str(result)
                })
                overall_stats['sites_failed'] += 1
            else:
                overall_stats['site_results'].append(result)
                overall_stats['sites_scraped'] += 1

                if result['success']:
                    overall_stats['sites_succeeded'] += 1
                    overall_stats['jobs_found'] += result['jobs_found']
                    overall_stats['jobs_new'] += result['jobs_new']
                    overall_stats['jobs_updated'] += result['jobs_updated']
                    overall_stats['jobs_unchanged'] += result['jobs_unchanged']
                    overall_stats['jobs_deactivated'] += result.get('jobs_deactivated', 0)
                else:
                    overall_stats['sites_failed'] += 1

        overall_stats['completed_at'] = datetime.now().isoformat()

        # Complete scrape run in database
        self.db.complete_scrape_run(run_id, {
            'sites_scraped': overall_stats['sites_scraped'],
            'jobs_found': overall_stats['jobs_found'],
            'jobs_new': overall_stats['jobs_new'],
            'jobs_updated': overall_stats['jobs_updated'],
            'jobs_deactivated': overall_stats['jobs_deactivated'],
            'status': 'completed'
        })

        return overall_stats

    async def scrape_all_sites_from_file(self, sites_file: str) -> Dict:
        """Scrape all sites from file.

        Args:
            sites_file: Path to file with site URLs

        Returns:
            Overall statistics
        """
        with open(sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip()]

        return await self.scrape_all_sites_incremental(sites)

    def generate_report(self, stats: Dict) -> str:
        """Generate human-readable report.

        Args:
            stats: Statistics from scrape

        Returns:
            Formatted report string
        """
        report = []
        report.append("="*80)
        report.append("ASYNC INCREMENTAL SCRAPE REPORT")
        report.append("="*80)
        report.append("")

        # Timing
        from datetime import datetime
        start = datetime.fromisoformat(stats['started_at'])
        end = datetime.fromisoformat(stats['completed_at'])
        duration = (end - start).total_seconds()

        report.append("## Timing")
        report.append("")
        report.append(f"Started:   {stats['started_at']}")
        report.append(f"Completed: {stats['completed_at']}")
        report.append(f"Duration:  {duration:.1f} seconds ({duration/60:.1f} minutes)")
        report.append("")

        # Overall stats
        report.append("## Overall Statistics")
        report.append("")
        report.append(f"Sites scraped: {stats['sites_scraped']}")
        report.append(f"  ✓ Succeeded: {stats['sites_succeeded']}")
        report.append(f"  ✗ Failed:    {stats['sites_failed']}")
        report.append("")
        report.append(f"Jobs found:      {stats['jobs_found']}")
        report.append(f"  • New:         {stats['jobs_new']}")
        report.append(f"  • Updated:     {stats['jobs_updated']}")
        report.append(f"  • Unchanged:   {stats['jobs_unchanged']}")
        report.append(f"  • Deactivated: {stats['jobs_deactivated']}")
        report.append("")

        # Performance metrics
        if stats['jobs_found'] > 0:
            jobs_per_second = stats['jobs_found'] / duration
            report.append(f"Performance: {jobs_per_second:.1f} jobs/second")

            new_pct = (stats['jobs_new'] / stats['jobs_found']) * 100
            report.append(f"New job rate: {new_pct:.1f}%")
            report.append("")

        # Per-site breakdown
        report.append("## Per-Site Results")
        report.append("")

        for site_result in stats['site_results']:
            if site_result.get('success'):
                report.append(f"✓ {site_result['url']}")
                report.append(f"    {site_result['jobs_found']} jobs "
                            f"({site_result['jobs_new']} new, "
                            f"{site_result['jobs_updated']} updated)")
                if site_result.get('stopped_early'):
                    report.append(f"    Stopped early (smart stop)")
            else:
                report.append(f"✗ {site_result['url']}")
                report.append(f"    Error: {site_result.get('error', 'Unknown')}")

        report.append("")

        # Database stats
        db_stats = self.db.get_stats()
        report.append("## Database Statistics")
        report.append("")
        report.append(f"Total jobs in database: {db_stats['total_jobs']}")
        report.append(f"  Active:   {db_stats['active_jobs']}")
        report.append(f"  Inactive: {db_stats['inactive_jobs']}")
        report.append("")
        report.append("Jobs by company:")
        for company, count in db_stats['jobs_by_company'].items():
            report.append(f"  • {company}: {count}")

        report.append("")
        report.append("="*80)

        return "\n".join(report)

    def save_report(self, stats: Dict, output_file: str):
        """Save report to file."""
        report = self.generate_report(stats)
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n✓ Report saved to {output_file}")

    def export_active_jobs(self, output_file: str):
        """Export active jobs to JSON."""
        import json
        jobs = self.db.get_active_jobs()
        with open(output_file, 'w') as f:
            json.dump(jobs, f, indent=2)
        print(f"✓ Exported {len(jobs)} active jobs to {output_file}")


async def main():
    """Run async incremental scrape."""
    sites_file = 'data/input/discovered_sites.txt'

    async with AsyncIncrementalScraper(
        db_path="data/jobs.db",
        use_url_detector=True,
        smart_stop_pages=5,
        max_concurrent_sites=3,
        max_concurrent_pages=3,
        rate_limit_delay=0.5
    ) as scraper:

        try:
            # Scrape all sites
            stats = await scraper.scrape_all_sites_from_file(sites_file)

            # Print report
            report = scraper.generate_report(stats)
            print("\n" + report)

            # Save report
            report_file = f"data/output/scrape_report_async_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            scraper.save_report(stats, report_file)

            # Export active jobs
            scraper.export_active_jobs('data/output/jobs_active_async.json')

            print("\n✅ Async incremental scrape completed successfully!")

        except Exception as e:
            print(f"\n❌ Scrape failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
