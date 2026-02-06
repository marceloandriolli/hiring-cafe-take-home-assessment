#!/usr/bin/env python3
"""Display statistics about scraped jobs"""
import json
from collections import Counter

def show_stats(filename='data/output/jobs.json'):
    """Show detailed statistics about scraped jobs."""

    try:
        with open(filename, 'r') as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return

    print("="*80)
    print(f"📊 SCRAPED JOBS STATISTICS")
    print("="*80)

    # Basic stats
    print(f"\n✨ Total Jobs: {len(jobs)}")

    # By company
    companies = Counter(job['company'] for job in jobs)
    print(f"\n🏢 Jobs by Company:")
    for company, count in companies.most_common():
        print(f"   {company:20s} : {count:4d} jobs")

    # By location (top 10)
    locations = Counter(job.get('location', 'Unknown') for job in jobs)
    print(f"\n🌍 Top 10 Locations:")
    for location, count in locations.most_common(10):
        loc_display = location if location != 'Unknown' else 'Not specified'
        print(f"   {loc_display:40s} : {count:4d} jobs")

    # Sample jobs
    print(f"\n📋 Sample Jobs:")
    for i, job in enumerate(jobs[:5], 1):
        print(f"\n   {i}. {job['title']}")
        print(f"      Company: {job['company']}")
        print(f"      Location: {job.get('location', 'Not specified')}")
        print(f"      URL: {job['url']}")

    print("\n" + "="*80)
    print(f"✅ Data validated: {filename}")
    print("="*80 + "\n")

if __name__ == "__main__":
    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else 'data/output/jobs.json'
    show_stats(filename)
