#!/usr/bin/env python3
"""Quick test of Lockheed Martin scraping"""
import sys
sys.path.insert(0, 'src')

from scraper import AvatureScraper

# Test Lockheed Martin with limited pages
scraper = AvatureScraper(use_url_detector=True)

# Modify max_pages for quick test
original_scrape = scraper.scrape_search_page

def quick_scrape(search_url, base_url):
    """Limited version for testing"""
    jobs = []
    page = 1
    max_pages = 3  # Only scrape 3 pages for test

    while page <= max_pages:
        print(f"  Page {page}...", end=' ')
        try:
            page_url = scraper.get_page_url(search_url, page)
            response = scraper.headers and requests.get(page_url, headers=scraper.headers, timeout=15) or None

            if not response or response.status_code != 200:
                print("No more jobs")
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.find_all('article')

            if not articles:
                print("No more jobs")
                break

            print(f"{len(articles)} jobs")

            for article in articles:
                job = scraper.extract_job_from_article(article, base_url)
                if job:
                    jobs.append(job)

            page += 1
            import time
            time.sleep(0.5)

        except Exception as e:
            print(f"Error: {e}")
            break

    return jobs

import requests
scraper.scrape_search_page = quick_scrape

print("="*80)
print("QUICK TEST: Lockheed Martin")
print("="*80)

jobs = scraper.scrape_site("https://lockheedmartin.avature.net/careers")

if jobs:
    print(f"\n✅ SUCCESS! Found {len(jobs)} jobs from Lockheed Martin")
    print(f"\nSample jobs:")
    for i, job in enumerate(jobs[:5], 1):
        print(f"  {i}. {job['title']}")
        print(f"     {job['url'][:100]}")
else:
    print(f"\n❌ FAILED: No jobs found")
