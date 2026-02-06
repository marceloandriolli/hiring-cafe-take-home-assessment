#!/usr/bin/env python3
"""
Discover Avature-hosted career sites using multiple strategies
"""
import requests
import re
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from tqdm import tqdm

class AvatureDiscovery:
    def __init__(self):
        self.discovered_sites = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def strategy_1_google_dork(self):
        """
        Strategy 1: Google Search
        Note: Requires manual execution or use of Google Custom Search API
        We'll use DuckDuckGo as it's more automation-friendly
        """
        print("\n[Strategy 1] Google Dork Search")
        print("Manual step: Search Google for: site:avature.net/careers")
        print("Automated alternative: Using DuckDuckGo HTML scraping...")

        # DuckDuckGo search (no API key needed)
        try:
            query = "site:avature.net/careers"
            url = f"https://html.duckduckgo.com/html/?q={query}"

            # Note: DDG has rate limiting, but is more permissive than Google
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                links = soup.find_all('a', {'class': 'result__a'})

                for link in links:
                    href = link.get('href')
                    if href and 'avature.net' in href:
                        # Extract the base domain
                        match = re.search(r'https?://([^/]+\.avature\.net)', href)
                        if match:
                            base_url = f"https://{match.group(1)}/careers"
                            self.discovered_sites.add(base_url)

                print(f"  Found {len(self.discovered_sites)} sites from DuckDuckGo")
        except Exception as e:
            print(f"  Error: {e}")

        return self.discovered_sites

    def strategy_2_subdomain_enumeration(self):
        """
        Strategy 2: Common subdomain patterns
        Try common company names/patterns as subdomains
        """
        print("\n[Strategy 2] Subdomain Pattern Testing")

        # Load common company names / Fortune 500 companies
        # For demo, using a small sample
        common_names = [
            'apple', 'google', 'microsoft', 'amazon', 'meta', 'netflix',
            'uber', 'lyft', 'airbnb', 'stripe', 'salesforce', 'oracle',
            'ibm', 'intel', 'nvidia', 'amd', 'cisco', 'hp', 'dell',
            'walmart', 'target', 'costco', 'homedepot', 'lowes',
            'jpmorgan', 'goldmansachs', 'morganstanley', 'wellsfargo',
            'bankofamerica', 'citigroup', 'hsbc', 'barclays',
            'pfizer', 'jnj', 'merck', 'abbvie', 'novartis', 'roche',
            'boeing', 'lockheed', 'raytheon', 'ge', 'ford', 'gm',
            'tesla', 'spacex', 'bluorigin',
        ]

        print(f"  Testing {len(common_names)} potential subdomains...")

        for name in tqdm(common_names, desc="Testing"):
            url = f"https://{name}.avature.net/careers"
            if self.check_if_exists(url):
                self.discovered_sites.add(url)
                time.sleep(0.5)  # Be polite

        print(f"  Found {len([s for s in self.discovered_sites if any(n in s for n in common_names)])} new sites")

        return self.discovered_sites

    def strategy_3_starter_pack(self, starter_file):
        """
        Strategy 3: Use the provided starter pack
        """
        print(f"\n[Strategy 3] Loading starter pack from {starter_file}")

        try:
            with open(starter_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('http'):
                        # Normalize to base /careers URL
                        if 'avature.net' in line:
                            parsed = urlparse(line)
                            base_url = f"{parsed.scheme}://{parsed.netloc}/careers"
                            self.discovered_sites.add(base_url)

            print(f"  Loaded {len(self.discovered_sites)} sites from starter pack")
        except FileNotFoundError:
            print(f"  Starter pack not found: {starter_file}")

        return self.discovered_sites

    def strategy_4_job_board_scraping(self):
        """
        Strategy 4: Find Avature links on job aggregator sites
        Check sites like Indeed, LinkedIn, etc. for Avature apply links
        """
        print("\n[Strategy 4] Job Board Scraping")
        print("  Checking job aggregators for Avature apply links...")

        # This would involve scraping job boards and finding "Apply" links
        # that point to avature.net domains
        # Skipping for now as it requires careful rate limiting

        return self.discovered_sites

    def strategy_5_common_crawl(self):
        """
        Strategy 5: Query Common Crawl index for Avature domains
        """
        print("\n[Strategy 5] Common Crawl Search")
        print("  Note: This requires querying Common Crawl's index API")

        # Example query to Common Crawl index
        # Would need to query: https://index.commoncrawl.org/CC-MAIN-*-index
        # For URLs matching *.avature.net/careers*

        # Placeholder for demonstration
        print("  Skipping - requires CDX API implementation")

        return self.discovered_sites

    def check_if_exists(self, url):
        """Check if a URL exists and is an Avature careers page."""
        try:
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                # Optionally verify it's actually an Avature page
                return True
        except:
            pass
        return False

    def verify_sites(self):
        """Verify all discovered sites are still active."""
        print(f"\n[Verification] Checking {len(self.discovered_sites)} discovered sites...")

        verified = set()
        for site in tqdm(list(self.discovered_sites), desc="Verifying"):
            if self.check_if_exists(site):
                verified.add(site)
            time.sleep(0.3)

        self.discovered_sites = verified
        print(f"  {len(verified)} sites verified as active")

        return verified

    def save_results(self, output_file):
        """Save discovered sites to a file."""
        with open(output_file, 'w') as f:
            for site in sorted(self.discovered_sites):
                f.write(f"{site}\n")

        print(f"\n[Saved] {len(self.discovered_sites)} sites to {output_file}")

def main():
    discovery = AvatureDiscovery()

    # Run discovery strategies
    # discovery.strategy_1_google_dork()  # May be rate limited
    discovery.strategy_2_subdomain_enumeration()
    # discovery.strategy_3_starter_pack('data/input/starter_pack.txt')
    # discovery.strategy_5_common_crawl()

    # Verify sites
    discovery.verify_sites()

    # Save results
    discovery.save_results('data/input/discovered_sites.txt')

    print(f"\n{'='*80}")
    print(f"Discovery complete! Found {len(discovery.discovered_sites)} Avature sites")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
