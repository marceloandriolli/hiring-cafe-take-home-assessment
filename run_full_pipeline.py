#!/usr/bin/env python3
"""
Full pipeline: Discover sites, scrape jobs, generate stats
"""
import json
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print status."""
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"{'='*80}\n")

    result = subprocess.run(cmd, shell=True, capture_output=False)

    if result.returncode != 0:
        print(f"\n❌ Failed: {description}")
        return False

    print(f"\n✅ Completed: {description}")
    return True

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          AVATURE ATS SCRAPER - FULL PIPELINE                 ║
║                                                              ║
║  This will:                                                  ║
║  1. Discover Avature-hosted sites                          ║
║  2. Scrape all jobs from discovered sites                  ║
║  3. Generate statistics and summary                        ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Step 1: Discovery
    if not run_command(
        "/opt/homebrew/opt/python@3.9/bin/python3.9 src/enhanced_discovery.py",
        "Discovering Avature sites"
    ):
        sys.exit(1)

    # Step 2: Scraping
    if not run_command(
        "/opt/homebrew/opt/python@3.9/bin/python3.9 src/scrape_all.py",
        "Scraping all discovered sites"
    ):
        sys.exit(1)

    # Step 3: Generate summary
    print(f"\n{'='*80}")
    print("FINAL RESULTS")
    print(f"{'='*80}\n")

    # Load and analyze results
    with open('data/output/jobs_all.json', 'r') as f:
        jobs = json.load(f)

    companies = {}
    locations = {}
    for job in jobs:
        # Count by company
        company = job['company']
        companies[company] = companies.get(company, 0) + 1

        # Count by location
        location = job.get('location', 'Unknown')
        locations[location] = locations.get(location, 0) + 1

    print(f"📊 Total unique jobs scraped: {len(jobs)}")
    print(f"🏢 Total companies: {len(companies)}")
    print(f"🌍 Total unique locations: {len(locations)}")
    print(f"\n📈 Top 5 companies by job count:")
    for i, (company, count) in enumerate(sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5], 1):
        print(f"   {i}. {company}: {count} jobs")

    print(f"\n🌎 Top 5 locations by job count:")
    for i, (location, count) in enumerate(sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5], 1):
        location_display = location if location != 'Unknown' else 'Unknown/Remote'
        print(f"   {i}. {location_display}: {count} jobs")

    print(f"\n✨ Data saved to: data/output/jobs_all.json")
    print(f"💾 File size: {Path('data/output/jobs_all.json').stat().st_size / 1024 / 1024:.2f} MB")

    print(f"\n{'='*80}")
    print("SUCCESS! Pipeline completed.")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
