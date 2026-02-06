#!/usr/bin/env python3
"""
Async scraper for concurrent site scraping.
Uses aiohttp for parallel HTTP requests and asyncio for concurrency.
"""

import asyncio
import aiohttp
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Import URL detector for pattern detection
try:
    from url_detector import AvatureURLDetector
    URL_DETECTOR_AVAILABLE = True
except ImportError:
    URL_DETECTOR_AVAILABLE = False


class AsyncAvatureScraper:
    """Async scraper for concurrent Avature site scraping."""

    def __init__(self, use_url_detector=True, max_concurrent_sites=5,
                 max_concurrent_pages=3, rate_limit_delay=0.5):
        """Initialize async scraper.

        Args:
            use_url_detector: Use URL detector for automatic pattern detection
            max_concurrent_sites: Maximum sites to scrape concurrently
            max_concurrent_pages: Maximum pages per site to scrape concurrently
            rate_limit_delay: Delay between requests in seconds
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.use_url_detector = use_url_detector and URL_DETECTOR_AVAILABLE

        # Concurrency limits
        self.max_concurrent_sites = max_concurrent_sites
        self.max_concurrent_pages = max_concurrent_pages
        self.rate_limit_delay = rate_limit_delay

        # URL detector (synchronous, but fast with cache)
        if self.use_url_detector:
            self.url_detector = AvatureURLDetector()
        else:
            self.url_detector = None

        # Session will be created in async context
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent_sites * self.max_concurrent_pages,
            limit_per_host=self.max_concurrent_pages
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def detect_pattern(self, base_url: str) -> Optional[str]:
        """Detect URL pattern (synchronous, uses cache).

        Args:
            base_url: Base URL of the site

        Returns:
            Pattern string or None
        """
        if self.use_url_detector and self.url_detector:
            return self.url_detector.detect_pattern(base_url)
        return None

    async def scrape_site(self, base_url: str, max_pages: int = 100) -> List[Dict]:
        """Scrape all jobs from a single site asynchronously.

        Args:
            base_url: Base URL of the Avature site
            max_pages: Maximum pages to scrape

        Returns:
            List of job dictionaries
        """
        print(f"\nScraping: {base_url}")

        try:
            # Detect URL pattern (synchronous but fast with cache)
            if self.use_url_detector and self.url_detector:
                pattern = self.detect_pattern(base_url)

                if pattern is None:
                    print(f"  ✗ No compatible URL pattern found")
                    return []

                search_url = f"{base_url}{pattern}"
            else:
                search_url = f"{base_url}/SearchJobs"

            # Scrape pages concurrently
            jobs = await self.scrape_search_pages_concurrent(
                search_url, base_url, max_pages
            )

            print(f"  Found {len(jobs)} jobs")
            return jobs

        except Exception as e:
            print(f"  Error: {e}")
            return []

    async def scrape_search_pages_concurrent(self, search_url: str,
                                            base_url: str,
                                            max_pages: int) -> List[Dict]:
        """Scrape multiple pages concurrently.

        Args:
            search_url: Base search URL
            base_url: Base site URL
            max_pages: Maximum pages to scrape

        Returns:
            List of jobs from all pages
        """
        all_jobs = []
        page = 1

        # Scrape first page to determine if there are more
        first_page_jobs = await self.scrape_single_page(
            search_url, base_url, page
        )

        if not first_page_jobs:
            return []

        all_jobs.extend(first_page_jobs)
        print(f"  Page 1: {len(first_page_jobs)} jobs")

        # Now scrape remaining pages concurrently in batches
        page = 2
        while page <= max_pages:
            # Create batch of page numbers
            batch_pages = list(range(page, min(page + self.max_concurrent_pages, max_pages + 1)))

            # Scrape batch concurrently
            tasks = [
                self.scrape_single_page(search_url, base_url, p)
                for p in batch_pages
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            empty_count = 0
            for page_num, result in zip(batch_pages, batch_results):
                if isinstance(result, Exception):
                    print(f"  Page {page_num}: Error - {result}")
                    empty_count += 1
                elif not result:
                    print(f"  Page {page_num}: No jobs (end)")
                    empty_count += 1
                else:
                    print(f"  Page {page_num}: {len(result)} jobs")
                    all_jobs.extend(result)

            # If all pages in batch were empty, stop
            if empty_count == len(batch_pages):
                break

            page += self.max_concurrent_pages

            # Rate limiting between batches
            if page <= max_pages:
                await asyncio.sleep(self.rate_limit_delay)

        return all_jobs

    async def scrape_single_page(self, search_url: str, base_url: str,
                                 page: int) -> List[Dict]:
        """Scrape a single page of jobs.

        Args:
            search_url: Base search URL
            base_url: Base site URL
            page: Page number

        Returns:
            List of jobs from this page
        """
        try:
            # Build page URL
            page_url = self.get_page_url(search_url, page)

            # Fetch page
            async with self.session.get(page_url) as response:
                if response.status != 200:
                    return []

                html = await response.text()

            # Parse HTML
            soup = BeautifulSoup(html, 'lxml')
            articles = soup.find_all('article')

            if not articles:
                return []

            # Extract jobs from articles
            jobs = []
            for article in articles:
                job = self.extract_job_from_article(article, base_url)
                if job:
                    jobs.append(job)

            return jobs

        except asyncio.TimeoutError:
            print(f"    Timeout on page {page}")
            return []
        except Exception as e:
            print(f"    Error on page {page}: {e}")
            return []

    def get_page_url(self, base_search_url: str, page: int) -> str:
        """Generate URL for a specific page number.

        Args:
            base_search_url: Base search URL
            page: Page number

        Returns:
            Full URL for the page
        """
        if page == 1:
            return base_search_url

        if '?' in base_search_url:
            return f"{base_search_url}&page={page}"
        else:
            return f"{base_search_url}?page={page}"

    def extract_job_from_article(self, article, base_url: str) -> Optional[Dict]:
        """Extract job information from an article element.

        Args:
            article: BeautifulSoup article element
            base_url: Base site URL

        Returns:
            Job dictionary or None
        """
        try:
            # Find the job link
            link = article.find('a', href=re.compile(r'JobDetail|FolderDetail', re.I))

            if not link:
                return None

            # Extract title
            title = link.get_text(strip=True)

            # Extract URL
            job_url = link.get('href')
            if not job_url.startswith('http'):
                job_url = urljoin(base_url, job_url)

            # Extract job ID from URL
            job_id_match = re.search(r'/(\d+)$', job_url)
            job_id = job_id_match.group(1) if job_id_match else None

            # Try to extract location
            location = None
            location_elem = article.find(attrs={'class': re.compile(r'location', re.I)})
            if location_elem:
                location = location_elem.get_text(strip=True)

            # Metadata
            metadata = {}
            date_elem = article.find('time')
            if date_elem:
                metadata['date_posted'] = date_elem.get('datetime') or date_elem.get_text(strip=True)

            job = {
                'title': title,
                'url': job_url,
                'job_id': job_id,
                'location': location,
                'company_url': base_url,
                'company': urlparse(base_url).netloc.split('.')[0],
                'scraped_at': datetime.now().isoformat(),
                'metadata': metadata,
            }

            return job

        except Exception as e:
            return None

    async def scrape_all_sites(self, sites: List[str],
                               max_pages_per_site: int = 100) -> List[Dict]:
        """Scrape multiple sites concurrently.

        Args:
            sites: List of site URLs
            max_pages_per_site: Maximum pages to scrape per site

        Returns:
            List of all jobs from all sites
        """
        print("="*80)
        print(f"ASYNC SCRAPE: {len(sites)} sites")
        print(f"Concurrency: {self.max_concurrent_sites} sites, "
              f"{self.max_concurrent_pages} pages per site")
        print("="*80)

        # Create semaphore to limit concurrent sites
        semaphore = asyncio.Semaphore(self.max_concurrent_sites)

        async def scrape_with_semaphore(site):
            """Scrape site with semaphore for rate limiting."""
            async with semaphore:
                jobs = await self.scrape_site(site, max_pages_per_site)
                # Rate limit between sites
                await asyncio.sleep(self.rate_limit_delay)
                return jobs

        # Scrape all sites concurrently
        tasks = [scrape_with_semaphore(site) for site in sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all jobs
        all_jobs = []
        for site, result in zip(sites, results):
            if isinstance(result, Exception):
                print(f"\n✗ {site}: Error - {result}")
            else:
                all_jobs.extend(result)

        return all_jobs

    async def scrape_all_sites_from_file(self, sites_file: str,
                                        max_pages_per_site: int = 100) -> List[Dict]:
        """Scrape all sites from a file.

        Args:
            sites_file: Path to file with site URLs (one per line)
            max_pages_per_site: Maximum pages per site

        Returns:
            List of all jobs
        """
        with open(sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip()]

        return await self.scrape_all_sites(sites, max_pages_per_site)


async def main():
    """Example usage of async scraper."""
    import sys

    sites_file = 'data/input/discovered_sites.txt'

    async with AsyncAvatureScraper(
        use_url_detector=True,
        max_concurrent_sites=3,      # Scrape 3 sites at once
        max_concurrent_pages=3,       # 3 pages per site concurrently
        rate_limit_delay=0.5
    ) as scraper:

        # Scrape all sites
        jobs = await scraper.scrape_all_sites_from_file(sites_file)

        print("\n" + "="*80)
        print(f"ASYNC SCRAPE COMPLETE")
        print("="*80)
        print(f"Total jobs: {len(jobs)}")

        # Group by company
        from collections import Counter
        companies = Counter(job['company'] for job in jobs)
        print(f"\nJobs by company:")
        for company, count in companies.most_common():
            print(f"  {company}: {count}")

        # Save results
        import json
        output_file = 'data/output/jobs_async.json'
        with open(output_file, 'w') as f:
            json.dump(jobs, f, indent=2)

        print(f"\n✓ Saved {len(jobs)} jobs to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
