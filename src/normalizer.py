#!/usr/bin/env python3
"""
Text normalization utilities for job deduplication.
Handles title and location normalization.
"""

import re
from typing import Dict, Optional


class TextNormalizer:
    """Normalizes job titles and locations for better matching."""

    # Title normalization mappings
    TITLE_ABBREVIATIONS = {
        # Seniority levels
        r'\bSr\.?\b': 'Senior',
        r'\bJr\.?\b': 'Junior',
        r'\bMgr\.?\b': 'Manager',
        r'\bDir\.?\b': 'Director',
        r'\bVP\b': 'Vice President',
        r'\bSVP\b': 'Senior Vice President',
        r'\bEVP\b': 'Executive Vice President',
        r'\bCTO\b': 'Chief Technology Officer',
        r'\bCEO\b': 'Chief Executive Officer',
        r'\bCFO\b': 'Chief Financial Officer',
        r'\bCOO\b': 'Chief Operating Officer',

        # Job roles
        r'\bEng\.?\b': 'Engineer',
        r'\bDev\.?\b': 'Developer',
        r'\bSWE\b': 'Software Engineer',
        r'\bQA\b': 'Quality Assurance',
        r'\bBA\b': 'Business Analyst',
        r'\bPM\b': 'Product Manager',
        r'\bTPM\b': 'Technical Program Manager',
        r'\bEM\b': 'Engineering Manager',
        r'\bSDE\b': 'Software Development Engineer',

        # Common terms
        r'\bIT\b': 'Information Technology',
        r'\bCS\b': 'Computer Science',
        r'\bUI\b': 'User Interface',
        r'\bUX\b': 'User Experience',
        r'\bML\b': 'Machine Learning',
        r'\bAI\b': 'Artificial Intelligence',
        r'\bAPI\b': 'Application Programming Interface',
        r'\bDB\b': 'Database',
        r'\bOps\b': 'Operations',
        r'\bDevOps\b': 'Development Operations',
        r'\bSRE\b': 'Site Reliability Engineer',
        r'\bFE\b': 'Frontend',
        r'\bBE\b': 'Backend',
        r'\bFS\b': 'Full Stack',
    }

    # Seniority level mappings
    SENIORITY_LEVELS = {
        'intern': 0,
        'internship': 0,
        'entry': 1,
        'entry level': 1,
        'junior': 2,
        'associate': 3,
        'mid': 4,
        'mid level': 4,
        'senior': 5,
        'staff': 6,
        'principal': 7,
        'lead': 7,
        'manager': 8,
        'senior manager': 9,
        'director': 10,
        'senior director': 11,
        'vice president': 12,
        'senior vice president': 13,
        'executive vice president': 14,
        'c-level': 15,
        'chief': 15,
    }

    # Location normalization
    STATE_ABBREVIATIONS = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
    }

    LOCATION_SYNONYMS = {
        'nyc': 'New York',
        'sf': 'San Francisco',
        'la': 'Los Angeles',
        'dc': 'Washington',
        'philly': 'Philadelphia',
        'chi': 'Chicago',
        'chi-town': 'Chicago',
    }

    def __init__(self):
        """Initialize normalizer."""
        pass

    def normalize_title(self, title: str) -> str:
        """Normalize a job title.

        Args:
            title: Raw job title

        Returns:
            Normalized title
        """
        if not title:
            return ""

        # Convert to title case
        normalized = title.strip().title()

        # Expand abbreviations
        for abbrev, full in self.TITLE_ABBREVIATIONS.items():
            normalized = re.sub(abbrev, full, normalized, flags=re.IGNORECASE)

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Remove special characters but keep important ones
        normalized = re.sub(r'[^\w\s\-/()&]', '', normalized)

        # Standardize separators
        normalized = normalized.replace('/', ' / ')
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def normalize_location(self, location: str) -> str:
        """Normalize a location string.

        Args:
            location: Raw location string

        Returns:
            Normalized location
        """
        if not location:
            return ""

        normalized = location.strip()

        # Remove "Remote" indicators
        if re.search(r'\b(remote|work from home|wfh)\b', normalized, re.IGNORECASE):
            return "Remote"

        # Expand common synonyms
        for abbrev, full in self.LOCATION_SYNONYMS.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            normalized = re.sub(pattern, full, normalized, flags=re.IGNORECASE)

        # Expand state abbreviations
        for abbrev, full in self.STATE_ABBREVIATIONS.items():
            # Match state abbreviation at end of string (e.g., "Seattle, WA")
            pattern = r',\s*' + abbrev + r'\b'
            normalized = re.sub(pattern, f', {full}', normalized)

        # Standardize format: "City, State" or "City, Country"
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def extract_seniority_level(self, title: str) -> Optional[int]:
        """Extract seniority level from title.

        Args:
            title: Job title

        Returns:
            Seniority level (0-15) or None
        """
        title_lower = title.lower()

        # Check for exact matches first
        for level_name, level_value in sorted(
            self.SENIORITY_LEVELS.items(),
            key=lambda x: -len(x[0])  # Longest match first
        ):
            if level_name in title_lower:
                return level_value

        return None

    def extract_key_terms(self, title: str) -> set:
        """Extract key terms from a job title.

        Args:
            title: Job title

        Returns:
            Set of key terms
        """
        # Normalize first
        normalized = self.normalize_title(title)

        # Remove seniority indicators
        for level in self.SENIORITY_LEVELS.keys():
            normalized = re.sub(
                r'\b' + re.escape(level) + r'\b',
                '',
                normalized,
                flags=re.IGNORECASE
            )

        # Remove common filler words
        filler_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
            'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can'
        }

        # Split into words
        words = normalized.lower().split()

        # Keep meaningful words (3+ characters, not filler)
        key_terms = {
            word for word in words
            if len(word) >= 3 and word not in filler_words
        }

        return key_terms

    def normalize_company_name(self, company: str) -> str:
        """Normalize company name.

        Args:
            company: Raw company name

        Returns:
            Normalized company name
        """
        if not company:
            return ""

        normalized = company.strip()

        # Remove common suffixes
        suffixes = [
            r'\bInc\.?$',
            r'\bLLC\.?$',
            r'\bLtd\.?$',
            r'\bCorp\.?$',
            r'\bCorporation$',
            r'\bLimited$',
            r'\bCompany$',
            r'\bCo\.?$',
        ]

        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Title case
        normalized = normalized.title()

        return normalized


def test_normalizer():
    """Test the normalizer."""
    normalizer = TextNormalizer()

    # Test title normalization
    print("Title Normalization:")
    test_titles = [
        "Sr. Software Engineer",
        "Jr. Developer",
        "VP of Engineering",
        "SWE - Machine Learning",
        "QA Eng.",
        "Product Mgr",
    ]

    for title in test_titles:
        normalized = normalizer.normalize_title(title)
        print(f"  '{title}' → '{normalized}'")

    print("\nLocation Normalization:")
    test_locations = [
        "NYC",
        "SF, CA",
        "Seattle, WA",
        "Remote",
        "Work from Home",
        "Chicago, IL",
    ]

    for location in test_locations:
        normalized = normalizer.normalize_location(location)
        print(f"  '{location}' → '{normalized}'")

    print("\nSeniority Extraction:")
    for title in test_titles:
        level = normalizer.extract_seniority_level(title)
        print(f"  '{title}' → Level {level}")

    print("\nKey Terms:")
    for title in test_titles:
        terms = normalizer.extract_key_terms(title)
        print(f"  '{title}' → {terms}")


if __name__ == "__main__":
    test_normalizer()
