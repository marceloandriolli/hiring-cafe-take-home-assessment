#!/usr/bin/env python3
"""
Reconnaissance script to understand Avature site structure and find API endpoints.
"""
import requests
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def fetch_page(url):
    """Fetch a page with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def find_api_endpoints(html, base_url):
    """Look for API endpoints in JavaScript and HTML."""
    soup = BeautifulSoup(html, 'lxml')

    # Find all script tags
    scripts = soup.find_all('script')

    endpoints = set()

    # Look for common API patterns
    patterns = [
        r'/api/[^\s"\']+',
        r'/careers/[^\s"\']+',
        r'SearchJobs',
        r'JobDetail',
        r'\.json[^\s"\']*',
    ]

    for script in scripts:
        if script.string:
            for pattern in patterns:
                matches = re.findall(pattern, script.string)
                endpoints.update(matches)

    # Also check for data attributes and meta tags
    for meta in soup.find_all('meta'):
        if meta.get('content'):
            for pattern in patterns:
                matches = re.findall(pattern, str(meta.get('content')))
                endpoints.update(matches)

    return endpoints

def test_endpoint(base_url, endpoint):
    """Test if an endpoint returns JSON data."""
    url = urljoin(base_url, endpoint)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                data = response.json()
                return True, data
            except:
                return False, None
    except:
        pass

    return False, None

def analyze_site(url):
    """Analyze an Avature site to find how it loads jobs."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {url}")
    print(f"{'='*80}\n")

    # Fetch the main page
    html = fetch_page(url)

    # Look for API endpoints
    endpoints = find_api_endpoints(html, url)
    print(f"Found {len(endpoints)} potential endpoints:")
    for ep in sorted(endpoints):
        print(f"  - {ep}")

    # Test some common Avature patterns
    test_urls = [
        '/careers/api/jobs',
        '/api/public/job',
        '/careers/JobList',
        '/careers/SearchJobs',
    ]

    print("\nTesting common endpoints:")
    for test_url in test_urls:
        full_url = urljoin(url, test_url)
        is_json, data = test_endpoint(url, test_url)
        if is_json:
            print(f"  ✓ {test_url} - Returns JSON!")
            print(f"    Keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
        else:
            print(f"  ✗ {test_url}")

    # Look for inline JSON data
    soup = BeautifulSoup(html, 'lxml')
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if 'JobPosting' in str(data):
                print("\n✓ Found JSON-LD job data!")
                print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        except:
            pass

if __name__ == "__main__":
    # Test the three example sites
    test_sites = [
        "https://bloomberg.avature.net/careers",
        "https://uclahealth.avature.net/careers",
        "https://cbs.avature.net/careers",
    ]

    for site in test_sites:
        try:
            analyze_site(site)
        except Exception as e:
            print(f"Error analyzing {site}: {e}")
