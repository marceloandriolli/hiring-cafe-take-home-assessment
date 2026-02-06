#!/usr/bin/env python3
"""
Fuzzy deduplication engine for job postings.
Uses normalized text and similarity metrics to detect duplicates.
"""

from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import difflib

try:
    from .normalizer import TextNormalizer
except ImportError:
    from normalizer import TextNormalizer


class FuzzyDeduplicator:
    """Detects duplicate jobs using fuzzy matching."""

    def __init__(self, title_threshold: float = 0.85,
                 location_threshold: float = 0.90,
                 combined_threshold: float = 0.80):
        """Initialize deduplicator.

        Args:
            title_threshold: Similarity threshold for titles (0-1)
            location_threshold: Similarity threshold for locations (0-1)
            combined_threshold: Combined similarity threshold (0-1)
        """
        self.title_threshold = title_threshold
        self.location_threshold = location_threshold
        self.combined_threshold = combined_threshold
        self.normalizer = TextNormalizer()

    def compute_similarity(self, str1: str, str2: str) -> float:
        """Compute similarity between two strings.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0-1)
        """
        if not str1 or not str2:
            return 0.0

        # Use SequenceMatcher for similarity
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def compute_jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """Compute Jaccard similarity between two sets.

        Args:
            set1: First set
            set2: Second set

        Returns:
            Jaccard similarity (0-1)
        """
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def are_jobs_similar(self, job1: Dict, job2: Dict) -> Tuple[bool, float, Dict]:
        """Check if two jobs are similar (potential duplicates).

        Args:
            job1: First job dictionary
            job2: Second job dictionary

        Returns:
            Tuple of (is_duplicate, similarity_score, details)
        """
        # Must be from same company
        company1 = self.normalizer.normalize_company_name(job1.get('company', ''))
        company2 = self.normalizer.normalize_company_name(job2.get('company', ''))

        if company1 != company2:
            return False, 0.0, {}

        # Normalize titles
        title1 = self.normalizer.normalize_title(job1.get('title', ''))
        title2 = self.normalizer.normalize_title(job2.get('title', ''))

        # Normalize locations
        loc1 = self.normalizer.normalize_location(job1.get('location', ''))
        loc2 = self.normalizer.normalize_location(job2.get('location', ''))

        # Compute title similarity
        title_similarity = self.compute_similarity(title1, title2)

        # Also check key terms overlap
        terms1 = self.normalizer.extract_key_terms(title1)
        terms2 = self.normalizer.extract_key_terms(title2)
        terms_similarity = self.compute_jaccard_similarity(terms1, terms2)

        # Use max of direct similarity and terms similarity
        title_score = max(title_similarity, terms_similarity)

        # Compute location similarity
        location_score = self.compute_similarity(loc1, loc2)

        # Special case: if both are "Remote", consider locations identical
        if loc1.lower() == "remote" and loc2.lower() == "remote":
            location_score = 1.0

        # Compute combined score (weighted average)
        # Title is more important than location
        combined_score = 0.7 * title_score + 0.3 * location_score

        # Check thresholds
        is_duplicate = (
            title_score >= self.title_threshold and
            location_score >= self.location_threshold and
            combined_score >= self.combined_threshold
        )

        details = {
            'title1': title1,
            'title2': title2,
            'location1': loc1,
            'location2': loc2,
            'title_similarity': title_similarity,
            'terms_similarity': terms_similarity,
            'title_score': title_score,
            'location_score': location_score,
            'combined_score': combined_score,
        }

        return is_duplicate, combined_score, details

    def find_duplicates(self, jobs: List[Dict]) -> Dict[str, List[Dict]]:
        """Find duplicate jobs in a list.

        Args:
            jobs: List of job dictionaries

        Returns:
            Dictionary mapping canonical job URL to list of duplicate jobs
        """
        # Group jobs by company first (optimization)
        jobs_by_company = defaultdict(list)
        for job in jobs:
            company = self.normalizer.normalize_company_name(job.get('company', ''))
            jobs_by_company[company].append(job)

        duplicates = {}
        processed = set()

        # Check each company's jobs
        for company, company_jobs in jobs_by_company.items():
            if len(company_jobs) < 2:
                continue  # No duplicates possible

            # Compare each pair of jobs
            for i, job1 in enumerate(company_jobs):
                job1_url = job1.get('url', '')

                if job1_url in processed:
                    continue

                # Check against remaining jobs
                for job2 in company_jobs[i+1:]:
                    job2_url = job2.get('url', '')

                    if job2_url in processed:
                        continue

                    # Check similarity
                    is_dup, score, details = self.are_jobs_similar(job1, job2)

                    if is_dup:
                        # Add to duplicates group
                        if job1_url not in duplicates:
                            duplicates[job1_url] = [job1]

                        duplicates[job1_url].append({
                            **job2,
                            '_similarity_score': score,
                            '_similarity_details': details
                        })

                        processed.add(job2_url)

        return duplicates

    def deduplicate_jobs(self, jobs: List[Dict],
                        keep_strategy: str = 'first') -> Tuple[List[Dict], List[Dict]]:
        """Deduplicate a list of jobs.

        Args:
            jobs: List of job dictionaries
            keep_strategy: Which job to keep ('first', 'last', 'most_recent')

        Returns:
            Tuple of (unique_jobs, removed_duplicates)
        """
        duplicates = self.find_duplicates(jobs)

        # Track which jobs to remove
        urls_to_remove = set()
        for canonical_url, dup_group in duplicates.items():
            # Keep the first job (canonical), remove others
            for dup_job in dup_group[1:]:  # Skip first (canonical)
                urls_to_remove.add(dup_job.get('url', ''))

        # Split into unique and duplicates
        unique_jobs = []
        removed_duplicates = []

        for job in jobs:
            job_url = job.get('url', '')
            if job_url in urls_to_remove:
                removed_duplicates.append(job)
            else:
                unique_jobs.append(job)

        return unique_jobs, removed_duplicates

    def generate_duplicate_report(self, jobs: List[Dict]) -> str:
        """Generate a human-readable duplicate report.

        Args:
            jobs: List of job dictionaries

        Returns:
            Formatted report string
        """
        duplicates = self.find_duplicates(jobs)

        if not duplicates:
            return "No duplicates found."

        report = []
        report.append("="*80)
        report.append("DUPLICATE JOBS REPORT")
        report.append("="*80)
        report.append("")

        total_duplicates = sum(len(group) - 1 for group in duplicates.values())
        report.append(f"Found {len(duplicates)} duplicate groups "
                     f"({total_duplicates} duplicate jobs)")
        report.append("")

        for i, (canonical_url, dup_group) in enumerate(duplicates.items(), 1):
            canonical = dup_group[0]
            duplicates_list = dup_group[1:]

            report.append(f"## Group {i}: {len(duplicates_list)} duplicate(s)")
            report.append("")
            report.append(f"**Canonical Job:**")
            report.append(f"  Title: {canonical.get('title', 'N/A')}")
            report.append(f"  Company: {canonical.get('company', 'N/A')}")
            report.append(f"  Location: {canonical.get('location', 'N/A')}")
            report.append(f"  URL: {canonical_url[:80]}...")
            report.append("")

            report.append(f"**Duplicates:**")
            for j, dup in enumerate(duplicates_list, 1):
                score = dup.get('_similarity_score', 0)
                report.append(f"  {j}. {dup.get('title', 'N/A')}")
                report.append(f"     Location: {dup.get('location', 'N/A')}")
                report.append(f"     Similarity: {score:.2%}")
                report.append(f"     URL: {dup.get('url', 'N/A')[:70]}...")

            report.append("")

        report.append("="*80)
        report.append(f"Summary: {len(duplicates)} groups, {total_duplicates} duplicates")
        report.append("="*80)

        return "\n".join(report)

    def get_deduplication_stats(self, jobs: List[Dict]) -> Dict:
        """Get deduplication statistics.

        Args:
            jobs: List of job dictionaries

        Returns:
            Statistics dictionary
        """
        duplicates = self.find_duplicates(jobs)

        total_jobs = len(jobs)
        duplicate_groups = len(duplicates)
        total_duplicates = sum(len(group) - 1 for group in duplicates.values())
        unique_jobs = total_jobs - total_duplicates

        # Duplicate rate by company
        company_stats = defaultdict(lambda: {'total': 0, 'duplicates': 0})

        for job in jobs:
            company = job.get('company', 'Unknown')
            company_stats[company]['total'] += 1

        for dup_group in duplicates.values():
            company = dup_group[0].get('company', 'Unknown')
            company_stats[company]['duplicates'] += len(dup_group) - 1

        return {
            'total_jobs': total_jobs,
            'unique_jobs': unique_jobs,
            'duplicate_groups': duplicate_groups,
            'total_duplicates': total_duplicates,
            'duplicate_rate': total_duplicates / total_jobs if total_jobs > 0 else 0,
            'company_stats': dict(company_stats)
        }


def test_deduplicator():
    """Test the deduplicator."""
    deduplicator = FuzzyDeduplicator()

    # Test jobs with duplicates
    test_jobs = [
        {
            'url': 'https://example.com/job1',
            'company': 'TechCorp',
            'title': 'Sr. Software Engineer',
            'location': 'NYC'
        },
        {
            'url': 'https://example.com/job2',
            'company': 'TechCorp',
            'title': 'Senior Software Engineer',
            'location': 'New York'
        },
        {
            'url': 'https://example.com/job3',
            'company': 'TechCorp',
            'title': 'Software Engineer',
            'location': 'NYC'
        },
        {
            'url': 'https://example.com/job4',
            'company': 'OtherCorp',
            'title': 'Sr. Software Engineer',
            'location': 'SF'
        },
        {
            'url': 'https://example.com/job5',
            'company': 'TechCorp',
            'title': 'Senior SWE - Machine Learning',
            'location': 'New York, NY'
        },
    ]

    print("="*80)
    print("DEDUPLICATOR TEST")
    print("="*80)

    # Find duplicates
    duplicates = deduplicator.find_duplicates(test_jobs)

    print(f"\nFound {len(duplicates)} duplicate groups:")
    for canonical_url, dup_group in duplicates.items():
        print(f"\n  Canonical: {dup_group[0]['title']}")
        for dup in dup_group[1:]:
            score = dup.get('_similarity_score', 0)
            print(f"    - {dup['title']} (similarity: {score:.2%})")

    # Get stats
    stats = deduplicator.get_deduplication_stats(test_jobs)
    print(f"\n{'='*80}")
    print("STATISTICS")
    print(f"{'='*80}")
    print(f"Total jobs: {stats['total_jobs']}")
    print(f"Unique jobs: {stats['unique_jobs']}")
    print(f"Duplicate groups: {stats['duplicate_groups']}")
    print(f"Total duplicates: {stats['total_duplicates']}")
    print(f"Duplicate rate: {stats['duplicate_rate']:.1%}")

    # Generate report
    print(f"\n{deduplicator.generate_duplicate_report(test_jobs)}")


if __name__ == "__main__":
    test_deduplicator()
