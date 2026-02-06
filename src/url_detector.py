#!/usr/bin/env python3
"""
URL Pattern Detector for Avature Sites

Detects which URL pattern an Avature site uses by trying common patterns
and checking for job indicators in the HTML response.
"""
import requests
import re
import json
import os
from bs4 import BeautifulSoup
from typing import Optional, Dict
from datetime import datetime


class AvatureURLDetector:
    """Detect which URL pattern an Avature site uses"""

    # Common Avature URL patterns, ordered by frequency
    PATTERNS = [
        '/SearchJobs',        # Most common (Bloomberg, Tesco, UCLA)
        '/JobSearch',         # Alternative pattern
        '/FolderDetail',      # Folder-based view
        '/JobList',           # List pattern
        '/Opportunities',     # Some sites use this
        '',                   # Direct /careers page (fallback)
    ]

    def __init__(self, cache_file='data/pattern_cache.json'):
        """
        Initialize detector with optional pattern cache

        Args:
            cache_file: Path to JSON file for caching detected patterns
        """
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def _load_cache(self) -> Dict[str, str]:
        """Load pattern cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        """Save pattern cache to file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.cache_file) if os.path.dirname(self.cache_file) else '.', exist_ok=True)

        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def detect_pattern(self, base_url: str, force_refresh: bool = False) -> Optional[str]:
        """
        Try each pattern and return the first that works

        Args:
            base_url: Base URL like "https://company.avature.net/careers"
            force_refresh: Ignore cache and re-detect

        Returns:
            Working pattern path (e.g., "/SearchJobs"), or None if none work
        """
        # Check cache first
        if not force_refresh and base_url in self.cache:
            cached_pattern = self.cache[base_url]
            # Verify cached pattern still works
            if self._test_url(f"{base_url}{cached_pattern}"):
                print(f"  ✓ Using cached pattern: {cached_pattern}")
                return cached_pattern
            else:
                print(f"  ⚠ Cached pattern {cached_pattern} no longer works, re-detecting")

        # Try each pattern
        print(f"  🔍 Detecting URL pattern for {base_url}")
        for pattern in self.PATTERNS:
            test_url = f"{base_url}{pattern}"
            print(f"    Testing: {pattern if pattern else '(base URL)'}")

            if self._test_url(test_url):
                print(f"    ✓ Found working pattern: {pattern if pattern else '(base URL)'}")

                # Cache the result
                self.cache[base_url] = pattern
                self.cache['last_updated'] = datetime.now().isoformat()
                self._save_cache()

                return pattern

        print(f"    ✗ No compatible pattern found")
        return None

    def _test_url(self, url: str) -> bool:
        """
        Check if URL returns a valid job listing page

        Args:
            url: Full URL to test

        Returns:
            True if page contains job indicators
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            # Check status code
            if response.status_code != 200:
                return False

            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')

            # Look for job indicators
            indicators = [
                # Strategy 1: Look for article tags (most common)
                len(soup.find_all('article')) > 0,

                # Strategy 2: Look for elements with "job" in class name
                len(soup.find_all(attrs={'class': re.compile(r'job', re.I)})) > 0,

                # Strategy 3: Look for JobDetail or FolderDetail links
                len(soup.find_all('a', href=re.compile(r'JobDetail|FolderDetail', re.I))) > 0,

                # Strategy 4: Look for common job-related text patterns
                bool(re.search(r'jobs?\s+found|positions?\s+available|openings?',
                              response.text, re.I)),

                # Strategy 5: Look for search/filter elements
                len(soup.find_all(attrs={'class': re.compile(r'search|filter', re.I)})) > 0,
            ]

            # If any indicator is True, this is likely a job listing page
            return any(indicators)

        except requests.exceptions.Timeout:
            print(f"      ⏱ Timeout testing {url}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"      ✗ Error testing {url}: {str(e)[:50]}")
            return False
        except Exception as e:
            print(f"      ✗ Unexpected error: {str(e)[:50]}")
            return False

    def get_cache_stats(self) -> Dict:
        """Get statistics about the pattern cache"""
        stats = {
            'total_sites': len([k for k in self.cache.keys() if k != 'last_updated']),
            'patterns': {},
            'last_updated': self.cache.get('last_updated', 'Never')
        }

        # Count patterns
        for url, pattern in self.cache.items():
            if url == 'last_updated':
                continue
            pattern_name = pattern if pattern else '(base URL)'
            stats['patterns'][pattern_name] = stats['patterns'].get(pattern_name, 0) + 1

        return stats

    def clear_cache(self, site_url: Optional[str] = None):
        """
        Clear pattern cache

        Args:
            site_url: If provided, clear only this site. Otherwise clear all.
        """
        if site_url:
            if site_url in self.cache:
                del self.cache[site_url]
                self._save_cache()
                print(f"Cleared cache for {site_url}")
        else:
            self.cache = {}
            self._save_cache()
            print("Cleared entire pattern cache")


def main():
    """Test the URL detector"""
    detector = AvatureURLDetector()

    # Test sites
    test_sites = [
        "https://bloomberg.avature.net/careers",
        "https://uclahealth.avature.net/careers",
        "https://tesco.avature.net/careers",
        "https://lockheedmartin.avature.net/careers",
        "https://mckinsey.avature.net/careers",
        "https://fb.avature.net/careers",
    ]

    print("="*80)
    print("URL Pattern Detection Test")
    print("="*80)

    for site in test_sites:
        print(f"\n{site}")
        pattern = detector.detect_pattern(site)
        if pattern is not None:
            print(f"  ✅ Pattern: {pattern if pattern else '(base URL)'}")
        else:
            print(f"  ❌ No compatible pattern found")

    # Show cache stats
    print("\n" + "="*80)
    print("Cache Statistics")
    print("="*80)
    stats = detector.get_cache_stats()
    print(f"Total sites cached: {stats['total_sites']}")
    print(f"Last updated: {stats['last_updated']}")
    print(f"\nPattern distribution:")
    for pattern, count in sorted(stats['patterns'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count} sites")


if __name__ == "__main__":
    main()
