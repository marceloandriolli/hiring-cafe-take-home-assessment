#!/usr/bin/env python3
"""
Check if SearchJobs page contains actual job data
"""
import requests
from bs4 import BeautifulSoup
import re

def check_search_page(base_url):
    """Check if /careers/SearchJobs contains job listings."""
    url = f"{base_url}/SearchJobs"
    print(f"\nChecking: {url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers)
    html = response.text
    soup = BeautifulSoup(html, 'lxml')

    # Look for job-related elements
    print("Looking for job listings...")

    # Common patterns for job listings
    patterns = [
        ('article', {}),
        ('div', {'class': re.compile(r'job', re.I)}),
        ('li', {'class': re.compile(r'job', re.I)}),
        ('a', {'href': re.compile(r'JobDetail|FolderDetail', re.I)}),
    ]

    for tag, attrs in patterns:
        elements = soup.find_all(tag, attrs)
        if elements:
            print(f"\nFound {len(elements)} <{tag}> elements")

            # Show first few
            for i, elem in enumerate(elements[:5]):
                # Try to extract job title
                title = None
                if tag == 'a':
                    title = elem.get_text(strip=True)
                    href = elem.get('href')
                    print(f"  {i+1}. {title[:100]}")
                    print(f"     URL: {href}")
                else:
                    # Look for title within the element
                    title_elem = elem.find(['h2', 'h3', 'h4', 'a'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        print(f"  {i+1}. {title[:100]}")

            if len(elements) > 5:
                print(f"  ... and {len(elements) - 5} more")

    # Check for pagination info
    pagination = soup.find_all(attrs={'class': re.compile(r'pag', re.I)})
    if pagination:
        print(f"\nFound pagination: {len(pagination)} elements")

    # Check total jobs count
    for pattern in [r'(\d+)\s+(jobs?|positions?|openings?)', r'showing\s+\d+\s+of\s+(\d+)']:
        matches = re.findall(pattern, html, re.I)
        if matches:
            print(f"\nTotal jobs mentioned: {matches[0] if isinstance(matches[0], str) else matches[0][0]}")
            break

if __name__ == "__main__":
    sites = [
        "https://bloomberg.avature.net/careers",
        "https://uclahealth.avature.net/careers",
    ]

    for site in sites:
        check_search_page(site)
        print("\n" + "="*80)
