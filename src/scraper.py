#!/usr/bin/env python3
"""
Scrape jobs from discovered Avature sites
"""
import requests
import re
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
from datetime import datetime

# Import URL detector for pattern detection
try:
    from url_detector import AvatureURLDetector
    URL_DETECTOR_AVAILABLE = True
except ImportError:
    URL_DETECTOR_AVAILABLE = False
    print("Warning: url_detector not available, using default /SearchJobs pattern")

class AvatureScraper:
    def __init__(self, use_url_detector=True):
        """
        Initialize scraper

        Args:
            use_url_detector: Use URL detector for automatic pattern detection
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.jobs = []

        # Initialize URL detector if available and requested
        if use_url_detector and URL_DETECTOR_AVAILABLE:
            self.url_detector = AvatureURLDetector()
            self.use_url_detector = True
        else:
            self.url_detector = None
            self.use_url_detector = False

    def scrape_site(self, base_url):
        """Scrape all jobs from a single Avature site with automatic pattern detection."""
        print(f"\nScraping: {base_url}")

        try:
            # Detect URL pattern if detector is available
            if self.use_url_detector and self.url_detector:
                pattern = self.url_detector.detect_pattern(base_url)

                if pattern is None:
                    print(f"  ✗ No compatible URL pattern found for {base_url}")
                    return []

                search_url = f"{base_url}{pattern}"
            else:
                # Fallback to default pattern
                search_url = f"{base_url}/SearchJobs"

            jobs = self.scrape_search_page(search_url, base_url)

            print(f"  Found {len(jobs)} jobs")
            return jobs

        except Exception as e:
            print(f"  Error: {e}")
            return []

    def scrape_search_page(self, search_url, base_url):
        """Scrape jobs from the search/listing page with pagination."""
        jobs = []
        page = 1
        max_pages = 100  # Safety limit

        while page <= max_pages:
            print(f"  Page {page}...", end=' ')

            try:
                # Some sites use ?page=X, others use different patterns
                # Try common patterns
                page_url = self.get_page_url(search_url, page)

                response = requests.get(page_url, headers=self.headers, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'lxml')

                # Find job articles
                articles = soup.find_all('article')

                if not articles:
                    print("No more jobs")
                    break

                print(f"{len(articles)} jobs")

                for article in articles:
                    job = self.extract_job_from_article(article, base_url)
                    if job:
                        jobs.append(job)

                # Check if there's a next page
                # Look for pagination controls
                next_button = soup.find('a', {'class': re.compile(r'next|pagination', re.I)})
                pagination_links = soup.find_all('a', href=re.compile(r'page=\d+'))

                if not next_button and not pagination_links:
                    # No more pages
                    break

                page += 1
                time.sleep(0.5)  # Be polite

            except Exception as e:
                print(f"Error on page {page}: {e}")
                break

        return jobs

    def get_page_url(self, base_search_url, page):
        """Generate URL for a specific page number."""
        if page == 1:
            return base_search_url

        # Try common pagination patterns
        if '?' in base_search_url:
            return f"{base_search_url}&page={page}"
        else:
            return f"{base_search_url}?page={page}"

    def extract_job_from_article(self, article, base_url):
        """Extract job information from an article element."""
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

            # Try to extract location from article
            location = None
            location_elem = article.find(attrs={'class': re.compile(r'location', re.I)})
            if location_elem:
                location = location_elem.get_text(strip=True)

            # Try to extract other metadata
            metadata = {}

            # Look for date posted
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
                'description': None,  # Will be filled by scrape_job_detail if needed
            }

            return job

        except Exception as e:
            print(f"    Error extracting job: {e}")
            return None

    def scrape_job_detail(self, job_url):
        """Scrape full job description from detail page."""
        try:
            response = requests.get(job_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            # Find the job description
            # Common patterns:
            desc_elem = (
                soup.find('div', {'class': re.compile(r'description|content|detail', re.I)}) or
                soup.find('section', {'class': re.compile(r'description|content|detail', re.I)}) or
                soup.find('article')
            )

            if desc_elem:
                # Get clean HTML or text
                description_html = str(desc_elem)
                description_text = desc_elem.get_text(separator='\n', strip=True)

                return {
                    'description_html': description_html,
                    'description_text': description_text,
                }

        except Exception as e:
            print(f"      Error scraping detail: {e}")

        return None

    def scrape_all_sites(self, sites_file, include_descriptions=False):
        """Scrape jobs from all sites in the file."""
        with open(sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip()]

        print(f"Scraping {len(sites)} Avature sites...")

        all_jobs = []

        for site in sites:
            jobs = self.scrape_site(site)
            all_jobs.extend(jobs)
            time.sleep(1)  # Be extra polite between sites

        # Optionally scrape full descriptions
        if include_descriptions:
            print(f"\nScraping {len(all_jobs)} job descriptions...")
            for job in tqdm(all_jobs, desc="Details"):
                details = self.scrape_job_detail(job['url'])
                if details:
                    job.update(details)
                time.sleep(0.3)

        self.jobs = all_jobs
        return all_jobs

    def save_results(self, output_file):
        """Save jobs to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.jobs, f, indent=2)

        print(f"\n{'='*80}")
        print(f"Saved {len(self.jobs)} jobs to {output_file}")
        print(f"{'='*80}")

def main():
    scraper = AvatureScraper()

    # Scrape all discovered sites
    sites_file = 'data/input/discovered_sites.txt'
    jobs = scraper.scrape_all_sites(sites_file, include_descriptions=False)

    # Save results
    scraper.save_results('data/output/jobs.json')

    # Print summary
    companies = set(job['company'] for job in jobs)
    print(f"\nSummary:")
    print(f"  Total jobs: {len(jobs)}")
    print(f"  Companies: {len(companies)}")
    print(f"  Average per company: {len(jobs) / len(companies):.1f}")

if __name__ == "__main__":
    main()
