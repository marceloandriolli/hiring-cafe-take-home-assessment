#!/usr/bin/env python3
"""
Scrape all discovered sites and combine with existing data
"""
import json
from scraper import AvatureScraper

def main():
    scraper = AvatureScraper()

    # Scrape the enhanced discovery list
    sites_file = 'data/input/enhanced_discovered_sites.txt'
    jobs = scraper.scrape_all_sites(sites_file, include_descriptions=False)

    # Save results
    scraper.save_results('data/output/jobs_all.json')

    # Print detailed summary
    print(f"\n{'='*80}")
    print("DETAILED SUMMARY")
    print(f"{'='*80}")

    companies = {}
    for job in jobs:
        company = job['company']
        if company not in companies:
            companies[company] = 0
        companies[company] += 1

    print(f"\nJobs per company:")
    for company in sorted(companies.keys()):
        print(f"  {company}: {companies[company]} jobs")

    print(f"\n  Total jobs: {len(jobs)}")
    print(f"  Total companies: {len(companies)}")
    print(f"  Average per company: {len(jobs) / len(companies):.1f}")

if __name__ == "__main__":
    main()
