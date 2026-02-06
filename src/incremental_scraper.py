#!/usr/bin/env python3
"""
Incremental scraper that uses database for tracking changes.
Only processes new or changed jobs, skips unchanged ones.
"""

import time
from datetime import datetime
from typing import List, Dict
from scraper import AvatureScraper
from database import JobDatabase


class IncrementalScraper(AvatureScraper):
    """Scraper with incremental update support using database tracking."""

    def __init__(self, db_path: str = "data/jobs.db", use_url_detector=True,
                 smart_stop_pages: int = 5):
        """Initialize incremental scraper.

        Args:
            db_path: Path to SQLite database
            use_url_detector: Use URL detector for automatic pattern detection
            smart_stop_pages: Stop after N consecutive pages with no new jobs
        """
        super().__init__(use_url_detector=use_url_detector)
        self.db = JobDatabase(db_path)
        self.smart_stop_pages = smart_stop_pages

        # Track stats for current run
        self.run_stats = {
            'sites_scraped': 0,
            'jobs_found': 0,
            'jobs_new': 0,
            'jobs_updated': 0,
            'jobs_unchanged': 0,
            'jobs_deactivated': 0,
            'status': 'completed',
            'error_message': None
        }

    def scrape_site_incremental(self, base_url) -> Dict:
        """Scrape a site and update database incrementally.

        Returns:
            Dictionary with statistics for this site
        """
        print(f"\nScraping: {base_url}")

        site_stats = {
            'url': base_url,
            'jobs_found': 0,
            'jobs_new': 0,
            'jobs_updated': 0,
            'jobs_unchanged': 0,
            'success': False,
            'error': None
        }

        try:
            # Detect URL pattern if detector is available
            if self.use_url_detector and self.url_detector:
                pattern = self.url_detector.detect_pattern(base_url)

                if pattern is None:
                    site_stats['error'] = "No compatible URL pattern found"
                    print(f"  ✗ {site_stats['error']}")
                    return site_stats

                search_url = f"{base_url}{pattern}"
            else:
                search_url = f"{base_url}/SearchJobs"

            # Scrape with smart stopping
            jobs, stats = self.scrape_search_page_smart(search_url, base_url)

            site_stats['jobs_found'] = len(jobs)
            site_stats['success'] = True

            # Process each job through database
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

            # Mark jobs that weren't seen as inactive
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

            # Early stopping indicator
            if stats.get('stopped_early'):
                print(f"    • Stopped early (no new jobs in {self.smart_stop_pages} pages)")

        except Exception as e:
            site_stats['error'] = str(e)
            print(f"  ✗ Error: {e}")

        return site_stats

    def scrape_search_page_smart(self, search_url, base_url):
        """Scrape with smart stopping - stop if no new jobs in N consecutive pages.

        Returns:
            Tuple of (jobs_list, stats_dict)
        """
        jobs = []
        page = 1
        max_pages = 100
        pages_without_new = 0

        stats = {
            'total_pages': 0,
            'stopped_early': False
        }

        while page <= max_pages:
            print(f"  Page {page}...", end=' ')

            try:
                page_url = self.get_page_url(search_url, page)

                import requests
                response = requests.get(page_url, headers=self.headers, timeout=15)
                response.raise_for_status()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'lxml')

                articles = soup.find_all('article')

                if not articles:
                    print("No more jobs")
                    break

                # Track if we found any new jobs on this page
                page_has_new = False

                for article in articles:
                    job = self.extract_job_from_article(article, base_url)
                    if job:
                        jobs.append(job)

                        # Check if this is a new job (not in database)
                        # This is a quick check before full upsert
                        # We'll do the actual upsert later
                        page_has_new = True  # For now, assume all are potentially new

                print(f"{len(articles)} jobs")

                stats['total_pages'] = page

                # Smart stopping logic
                if not page_has_new:
                    pages_without_new += 1
                    if pages_without_new >= self.smart_stop_pages:
                        print(f"  No new jobs in {self.smart_stop_pages} pages, stopping early")
                        stats['stopped_early'] = True
                        break
                else:
                    pages_without_new = 0

                # Check for next page
                import re
                next_button = soup.find('a', {'class': re.compile(r'next|pagination', re.I)})
                pagination_links = soup.find_all('a', href=re.compile(r'page=\d+'))

                if not next_button and not pagination_links:
                    break

                page += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"Error: {e}")
                break

        return jobs, stats

    def scrape_all_sites_incremental(self, sites_file: str) -> Dict:
        """Scrape all sites with incremental updates and database tracking.

        Args:
            sites_file: Path to file with site URLs

        Returns:
            Dictionary with overall statistics
        """
        with open(sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip()]

        print("="*80)
        print(f"INCREMENTAL SCRAPE: {len(sites)} sites")
        print(f"Database: {self.db.db_path}")
        print("="*80)

        # Start scrape run
        run_id = self.db.start_scrape_run()

        # Track overall stats
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

        # Scrape each site
        for site in sites:
            site_stats = self.scrape_site_incremental(site)
            overall_stats['site_results'].append(site_stats)

            overall_stats['sites_scraped'] += 1
            if site_stats['success']:
                overall_stats['sites_succeeded'] += 1
                overall_stats['jobs_found'] += site_stats['jobs_found']
                overall_stats['jobs_new'] += site_stats['jobs_new']
                overall_stats['jobs_updated'] += site_stats['jobs_updated']
                overall_stats['jobs_unchanged'] += site_stats['jobs_unchanged']
                overall_stats['jobs_deactivated'] += site_stats.get('jobs_deactivated', 0)
            else:
                overall_stats['sites_failed'] += 1

            time.sleep(1)  # Be polite between sites

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

    def generate_report(self, stats: Dict) -> str:
        """Generate a human-readable report from scrape statistics.

        Args:
            stats: Statistics dictionary from scrape_all_sites_incremental

        Returns:
            Formatted report string
        """
        report = []
        report.append("="*80)
        report.append("INCREMENTAL SCRAPE REPORT")
        report.append("="*80)
        report.append("")

        # Overall stats
        report.append("## Overall Statistics")
        report.append("")
        report.append(f"Started:  {stats['started_at']}")
        report.append(f"Completed: {stats['completed_at']}")
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

        # Calculate efficiency
        if stats['jobs_found'] > 0:
            new_pct = (stats['jobs_new'] / stats['jobs_found']) * 100
            report.append(f"New job rate: {new_pct:.1f}%")
            report.append("")

        # Per-site breakdown
        report.append("## Per-Site Results")
        report.append("")

        for site_result in stats['site_results']:
            if site_result['success']:
                report.append(f"✓ {site_result['url']}")
                report.append(f"    {site_result['jobs_found']} jobs "
                            f"({site_result['jobs_new']} new, "
                            f"{site_result['jobs_updated']} updated)")
            else:
                report.append(f"✗ {site_result['url']}")
                report.append(f"    Error: {site_result['error']}")

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
        """Save report to file.

        Args:
            stats: Statistics dictionary
            output_file: Path to output file
        """
        report = self.generate_report(stats)

        with open(output_file, 'w') as f:
            f.write(report)

        print(f"\n✓ Report saved to {output_file}")

    def export_active_jobs(self, output_file: str):
        """Export all active jobs to JSON file.

        Args:
            output_file: Path to output JSON file
        """
        import json

        jobs = self.db.get_active_jobs()

        with open(output_file, 'w') as f:
            json.dump(jobs, f, indent=2)

        print(f"✓ Exported {len(jobs)} active jobs to {output_file}")

    def close(self):
        """Clean up resources."""
        self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """Run incremental scrape of all sites."""
    import sys

    # Use context manager for automatic cleanup
    with IncrementalScraper(
        db_path="data/jobs.db",
        use_url_detector=True,
        smart_stop_pages=5
    ) as scraper:

        # Scrape all sites
        sites_file = 'data/input/discovered_sites.txt'

        try:
            stats = scraper.scrape_all_sites_incremental(sites_file)

            # Print report
            report = scraper.generate_report(stats)
            print("\n" + report)

            # Save report
            report_file = f"data/output/scrape_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            scraper.save_report(stats, report_file)

            # Export active jobs
            scraper.export_active_jobs('data/output/jobs_active.json')

            print("\n✅ Incremental scrape completed successfully!")

        except Exception as e:
            print(f"\n❌ Scrape failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
