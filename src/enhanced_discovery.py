#!/usr/bin/env python3
"""
Enhanced Avature site discovery using multiple advanced strategies
"""
import requests
import re
import time
from urllib.parse import urlparse
from tqdm import tqdm
import json

class EnhancedDiscovery:
    def __init__(self):
        self.discovered_sites = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def strategy_a_expanded_subdomains(self):
        """
        Test expanded list of company names from multiple sources
        """
        print("\n[Strategy A] Expanded Subdomain Testing")

        # Fortune 500 + Tech + Healthcare + Financial + More
        companies = self.load_company_list()

        print(f"Testing {len(companies)} potential subdomains...")

        found = 0
        for company in tqdm(companies, desc="Testing"):
            url = f"https://{company}.avature.net/careers"
            if self.check_and_add(url):
                found += 1
            time.sleep(0.2)  # Be polite

        print(f"  Found {found} new sites via subdomain testing")
        return self.discovered_sites

    def load_company_list(self):
        """
        Generate comprehensive list of potential company subdomains
        """
        # Common company name patterns
        companies = set()

        # Technology Companies
        tech = [
            'apple', 'google', 'alphabet', 'microsoft', 'amazon', 'amzn',
            'meta', 'fb', 'facebook', 'netflix', 'uber', 'lyft', 'airbnb',
            'stripe', 'salesforce', 'oracle', 'ibm', 'intel', 'nvidia',
            'amd', 'cisco', 'dell', 'hp', 'vmware', 'servicenow', 'workday',
            'adobe', 'autodesk', 'intuit', 'paypal', 'square', 'twilio',
            'snowflake', 'databricks', 'atlassian', 'slack', 'zoom',
            'spotify', 'dropbox', 'box', 'docusign', 'zendesk',
        ]

        # Financial Services
        finance = [
            'jpmorgan', 'jpmc', 'jpm', 'goldmansachs', 'gs',
            'morganstanley', 'ms', 'wellsfargo', 'wf', 'bankofamerica', 'boa',
            'citigroup', 'citi', 'hsbc', 'barclays', 'deutschebank', 'db',
            'ubs', 'creditsuisse', 'blackrock', 'vanguard', 'fidelity',
            'schwab', 'tdameritrade', 'etrade', 'capitalone', 'discover',
            'americanexpress', 'amex', 'visa', 'mastercard', 'paypal',
        ]

        # Healthcare & Pharma
        healthcare = [
            'pfizer', 'jnj', 'johnsonjohnson', 'merck', 'abbvie',
            'novartis', 'roche', 'bms', 'bristolmyers', 'lilly',
            'gilead', 'amgen', 'biogen', 'regeneron', 'moderna',
            'johnshopkins', 'mayoclinic', 'clevelandclinic',
            'kaiserpermanente', 'kp', 'ucla', 'uclahealth',
            'sutterhealth', 'dignityhealth', 'hca', 'tenet',
            'unitedhealth', 'uhg', 'anthem', 'cigna', 'aetna', 'humana',
        ]

        # Consulting & Professional Services
        consulting = [
            'mckinsey', 'bain', 'bcg', 'deloitte', 'pwc', 'ey',
            'kpmg', 'accenture', 'booz', 'oliverwyman', 'bain',
        ]

        # Retail & Consumer
        retail = [
            'walmart', 'target', 'costco', 'homedepot', 'lowes',
            'amazon', 'ebay', 'walgreens', 'cvs', 'kroger', 'albertsons',
            'macys', 'nordstrom', 'gap', 'nike', 'adidas', 'underarmour',
            'lululemon', 'tjx', 'ross', 'bestbuy', 'staples',
        ]

        # Media & Entertainment
        media = [
            'disney', 'comcast', 'nbcuniversal', 'viacom', 'paramount',
            'warnermedia', 'att', 'verizon', 'tmobile', 'sprint',
            'cbs', 'nbc', 'abc', 'fox', 'cnn', 'espn', 'hbo', 'showtime',
            'netflix', 'hulu', 'peacock', 'hbomax', 'paramount',
        ]

        # Aerospace & Defense
        aerospace = [
            'boeing', 'lockheed', 'lockheedmartin', 'raytheon', 'rtx',
            'northropgrumman', 'ng', 'gd', 'generaldynamics', 'l3harris',
            'bae', 'baesystems', 'airbus', 'spacex', 'bluorigin',
        ]

        # Automotive
        auto = [
            'ford', 'gm', 'generalmotors', 'toyota', 'honda', 'nissan',
            'volkswagen', 'vw', 'bmw', 'mercedes', 'mercedesbenz',
            'audi', 'porsche', 'tesla', 'rivian', 'lucid', 'nio',
        ]

        # Energy & Utilities
        energy = [
            'exxon', 'exxonmobil', 'chevron', 'shell', 'bp', 'total',
            'conocophillips', 'conocophillips', 'valero', 'marathon',
            'duke', 'southern', 'nextera', 'dominion', 'pge',
        ]

        # Combine all
        companies.update(tech)
        companies.update(finance)
        companies.update(healthcare)
        companies.update(consulting)
        companies.update(retail)
        companies.update(media)
        companies.update(aerospace)
        companies.update(auto)
        companies.update(energy)

        # Add variations (hyphenated, no spaces, etc.)
        variations = set()
        for company in list(companies):
            variations.add(company.replace(' ', ''))
            variations.add(company.replace(' ', '-'))
            variations.add(company.replace(' ', '_'))

        companies.update(variations)

        return sorted(companies)

    def strategy_b_reverse_dns_sweep(self):
        """
        Strategy B: Query DNS for *.avature.net subdomains
        This would require access to DNS zone files or services like:
        - SecurityTrails API
        - Rapid7 Sonar DNS data
        - Certificate Transparency logs
        """
        print("\n[Strategy B] Reverse DNS / Certificate Transparency")
        print("  Note: Requires API keys or CT log parsing")
        print("  Suggested services:")
        print("    - crt.sh (Certificate Transparency)")
        print("    - SecurityTrails API")
        print("    - Rapid7 Open Data")

        # Try crt.sh (free, no API key needed)
        try:
            url = "https://crt.sh/?q=%.avature.net&output=json"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                certs = response.json()
                subdomains = set()

                for cert in certs:
                    name = cert.get('name_value', '')
                    if 'avature.net' in name:
                        # Extract subdomain
                        parts = name.replace('*.', '').strip().split('\n')
                        for part in parts:
                            if '.avature.net' in part:
                                subdomain = part.split('.avature.net')[0].strip()
                                if subdomain and subdomain != '*':
                                    careers_url = f"https://{subdomain}.avature.net/careers"
                                    subdomains.add(careers_url)

                print(f"  Found {len(subdomains)} potential sites from crt.sh")

                # Verify them
                for site in tqdm(list(subdomains)[:100], desc="Verifying"):
                    self.check_and_add(site)
                    time.sleep(0.3)

        except Exception as e:
            print(f"  Error: {e}")

        return self.discovered_sites

    def strategy_c_google_search_api(self):
        """
        Strategy C: Use Google Custom Search API
        Requires API key
        """
        print("\n[Strategy C] Google Custom Search API")
        print("  Note: Requires GOOGLE_API_KEY and SEARCH_ENGINE_ID")
        print("  Skipping - add API key to enable")

        # Placeholder for API implementation
        # Would query: site:avature.net/careers

        return self.discovered_sites

    def check_and_add(self, url):
        """Check if URL exists and add to discovered set."""
        try:
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                self.discovered_sites.add(url)
                return True
        except:
            pass
        return False

    def save_results(self, output_file):
        """Save discovered sites."""
        with open(output_file, 'w') as f:
            for site in sorted(self.discovered_sites):
                f.write(f"{site}\n")

        print(f"\n[Saved] {len(self.discovered_sites)} sites to {output_file}")

def main():
    discovery = EnhancedDiscovery()

    # Run strategies
    discovery.strategy_a_expanded_subdomains()
    discovery.strategy_b_reverse_dns_sweep()

    # Save results
    discovery.save_results('data/input/enhanced_discovered_sites.txt')

    print(f"\n{'='*80}")
    print(f"Enhanced discovery complete! Found {len(discovery.discovered_sites)} sites")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
