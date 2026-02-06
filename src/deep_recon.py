#!/usr/bin/env python3
"""
Deep reconnaissance - Download full page and analyze all JavaScript
"""
import requests
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def deep_analyze(url):
    """Download and deeply analyze an Avature site."""
    print(f"\nDeep analysis of: {url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers)
    html = response.text
    soup = BeautifulSoup(html, 'lxml')

    # Strategy 1: Look for inline job data in HTML
    print("Strategy 1: Looking for inline job data...")
    job_links = soup.find_all('a', href=re.compile(r'JobDetail|career|job', re.I))
    if job_links:
        print(f"  Found {len(job_links)} job-related links")
        for link in job_links[:3]:
            print(f"    - {link.get('href')}")

    # Strategy 2: Check for JSON-LD structured data
    print("\nStrategy 2: Checking JSON-LD structured data...")
    ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in ld_scripts:
        try:
            data = json.loads(script.string)
            print(f"  Found JSON-LD: {type(data)} with keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        except:
            pass

    # Strategy 3: Look for data attributes
    print("\nStrategy 3: Looking for data attributes...")
    elements_with_data = soup.find_all(attrs={'data-job': True})
    if elements_with_data:
        print(f"  Found {len(elements_with_data)} elements with data-job attribute")

    # Strategy 4: Find all external script sources
    print("\nStrategy 4: External JavaScript files...")
    scripts = soup.find_all('script', src=True)
    script_urls = [s.get('src') for s in scripts if s.get('src')]
    print(f"  Found {len(script_urls)} external scripts")

    # Look for specific patterns in script URLs
    relevant_scripts = [s for s in script_urls if any(keyword in s.lower() for keyword in ['job', 'search', 'career', 'data'])]
    if relevant_scripts:
        print("  Relevant scripts:")
        for s in relevant_scripts:
            print(f"    - {s}")

    # Strategy 5: Look for API URLs in all script content
    print("\nStrategy 5: Searching for API patterns in JavaScript...")
    api_patterns = [
        r'[\'"]/(api|careers)/[^\'"]+[\'"]',
        r'fetch\([\'"]([^\'"]+)[\'"]',
        r'\.ajax\(\{[^}]*url:\s*[\'"]([^\'"]+)[\'"]',
        r'axios\.[a-z]+\([\'"]([^\'"]+)[\'"]',
    ]

    all_scripts = soup.find_all('script')
    found_urls = set()

    for script in all_scripts:
        if script.string:
            for pattern in api_patterns:
                matches = re.findall(pattern, script.string)
                found_urls.update(matches)

    if found_urls:
        print(f"  Found {len(found_urls)} potential API URLs:")
        for url_match in sorted(found_urls)[:15]:
            print(f"    - {url_match}")

    # Strategy 6: Look for AJAX configuration
    print("\nStrategy 6: Looking for AJAX configurations...")
    ajax_configs = re.findall(r'\$.ajax\s*\(\s*\{([^}]+)\}', html, re.DOTALL)
    if ajax_configs:
        print(f"  Found {len(ajax_configs)} AJAX configuration blocks")

    # Strategy 7: Check if jobs are server-side rendered in HTML
    print("\nStrategy 7: Checking for server-side rendered jobs...")
    job_titles = soup.find_all(attrs={'class': re.compile(r'job.*title', re.I)})
    if job_titles:
        print(f"  Found {len(job_titles)} elements with job-title-like classes")

    # Try to find the actual job listing section
    job_sections = soup.find_all(attrs={'class': re.compile(r'job.*list|search.*result', re.I)})
    if job_sections:
        print(f"  Found {len(job_sections)} job listing sections")

if __name__ == "__main__":
    sites = [
        "https://bloomberg.avature.net/careers",
        "https://uclahealth.avature.net/careers",
    ]

    for site in sites:
        deep_analyze(site)
        print("\n" + "="*80)
