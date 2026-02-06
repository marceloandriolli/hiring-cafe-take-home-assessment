#!/usr/bin/env python3
"""Test the discovery mechanism"""
from discovery import AvatureDiscovery

discovery = AvatureDiscovery()

# Test with known working sites
test_sites = [
    "https://bloomberg.avature.net/careers",
    "https://uclahealth.avature.net/careers",
]

print("Testing known working sites...")
for site in test_sites:
    exists = discovery.check_if_exists(site)
    print(f"  {site}: {'✓ EXISTS' if exists else '✗ NOT FOUND'}")

# Manually add them
print("\nAdding known sites manually...")
for site in test_sites:
    discovery.discovered_sites.add(site)

# Now let's try to find more by looking at common patterns
# Try more company variations
print("\nTrying more subdomain patterns...")

additional_patterns = [
    'ucla', 'uclahealth', 'bloomberg',  # Known working
    # Healthcare
    'johnshopkins', 'mayoclinic', 'clevelandclinic', 'kp', 'kaiserpermanente',
    # Tech companies using different names
    'fb', 'meta',  'alphabet',
    # Financial
    'jpmc', 'jpm', 'goldmansachs', 'gs', 'ms', 'morganstanley',
    # Retail/Consumer
    'walmart', 'target', 'amazon', 'amzn',
]

for pattern in additional_patterns:
    url = f"https://{pattern}.avature.net/careers"
    if discovery.check_if_exists(url):
        print(f"  ✓ Found: {url}")
        discovery.discovered_sites.add(url)

discovery.save_results('data/input/discovered_sites.txt')
print(f"\nTotal discovered: {len(discovery.discovered_sites)}")
