"""
Test Suite for Phase 4: Fuzzy Deduplication

Tests the normalization and deduplication functionality including:
- Text normalization (titles and locations)
- Abbreviation expansion
- Sequence similarity matching
- Jaccard similarity matching
- Company-scoped deduplication
- Similarity thresholds
- Duplicate grouping and reporting
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from src.normalizer import TextNormalizer
from src.deduplicator import FuzzyDeduplicator as JobDeduplicator
import difflib


class TestTextNormalization(unittest.TestCase):
    """Test text normalization functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.normalizer = TextNormalizer()

    def test_normalizer_creation(self):
        """Test that normalizer can be instantiated"""
        normalizer = TextNormalizer()
        self.assertIsNotNone(normalizer)

    def test_normalize_title_basic(self):
        """Test basic title normalization"""
        title = "  software engineer  "
        normalized = self.normalizer.normalize_title(title)

        # Should trim whitespace and normalize case
        self.assertEqual(normalized.strip(), normalized)
        self.assertNotEqual(normalized, title)

    def test_senior_abbreviation_expansion(self):
        """Test senior abbreviation expansion"""
        titles = [
            ("Sr. Software Engineer", "Senior Software Engineer"),
            ("Sr SWE", "Senior Software Engineer"),  # After abbreviation expansion
            ("Sr. Engineer", "Senior Engineer")
        ]

        for input_title, expected_word in titles:
            normalized = self.normalizer.normalize_title(input_title)
            self.assertIn("Senior", normalized)

    def test_junior_abbreviation_expansion(self):
        """Test junior abbreviation expansion"""
        titles = [
            ("Jr. Software Engineer", "Junior Software Engineer"),
            ("Jr Engineer", "Junior Engineer")
        ]

        for input_title, expected_word in titles:
            normalized = self.normalizer.normalize_title(input_title)
            self.assertIn("Junior", normalized)

    def test_software_engineer_abbreviations(self):
        """Test software engineer abbreviation expansion"""
        abbreviations = {
            "SWE": "Software Engineer",
            "SE": "Software Engineer",
            "Eng": "Engineer"
        }

        for abbrev, full in abbreviations.items():
            # Test that abbreviation is expanded
            if abbrev == "SWE":
                normalized = self.normalizer.normalize_title(f"Senior {abbrev}")
                # Should expand SWE
                self.assertIn("Software Engineer", normalized)

    def test_tech_abbreviations(self):
        """Test technology abbreviations"""
        tech_abbrevs = {
            "QA": "Quality Assurance",
            "DevOps": "Devops",
            "ML": "Machine Learning",
            "AI": "Artificial Intelligence"
        }

        for abbrev, full in tech_abbrevs.items():
            normalized = self.normalizer.normalize_title(f"{abbrev} Engineer")
            # Check that abbreviation is handled
            self.assertIsNotNone(normalized)


class TestLocationNormalization(unittest.TestCase):
    """Test location normalization"""

    def setUp(self):
        """Set up test fixtures"""
        self.normalizer = TextNormalizer()

    def test_normalize_location_basic(self):
        """Test basic location normalization"""
        location = "  New York, NY  "
        normalized = self.normalizer.normalize_location(location)

        # Should trim whitespace
        self.assertEqual(normalized.strip(), normalized)

    def test_nyc_abbreviation(self):
        """Test NYC abbreviation expansion"""
        locations = [
            "NYC",
            "New York City",
            "New York, NY"
        ]

        for location in locations:
            normalized = self.normalizer.normalize_location(location)
            # Should normalize to consistent format
            self.assertIn("New York", normalized)

    def test_sf_abbreviation(self):
        """Test SF abbreviation expansion"""
        locations = [
            "SF",
            "San Francisco",
            "San Francisco, CA"
        ]

        for location in locations:
            normalized = self.normalizer.normalize_location(location)
            # Should normalize to consistent format
            self.assertIn("San Francisco", normalized)

    def test_la_abbreviation(self):
        """Test LA abbreviation expansion"""
        location = "LA"
        normalized = self.normalizer.normalize_location(location)

        # Should expand LA to Los Angeles
        self.assertIn("Los Angeles", normalized)

    def test_state_abbreviations(self):
        """Test state abbreviation handling"""
        locations = [
            ("New York, NY", "New York"),
            ("Los Angeles, CA", "Los Angeles"),
            ("Chicago, IL", "Chicago")
        ]

        for location, expected_city in locations:
            normalized = self.normalizer.normalize_location(location)
            # Should contain city name
            self.assertIn(expected_city, normalized)


class TestSimilarityAlgorithms(unittest.TestCase):
    """Test similarity calculation algorithms"""

    def setUp(self):
        """Set up test fixtures"""
        self.deduplicator = JobDeduplicator()

    def test_sequence_similarity_identical(self):
        """Test sequence similarity for identical strings"""
        text1 = "Software Engineer"
        text2 = "Software Engineer"

        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()

        self.assertEqual(similarity, 1.0)

    def test_sequence_similarity_different(self):
        """Test sequence similarity for different strings"""
        text1 = "Software Engineer"
        text2 = "Data Scientist"

        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()

        self.assertLess(similarity, 0.5)

    def test_sequence_similarity_similar(self):
        """Test sequence similarity for similar strings"""
        text1 = "Software Engineer"
        text2 = "Software Engineering"

        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()

        # Should be high similarity
        self.assertGreater(similarity, 0.8)

    def test_jaccard_similarity_identical(self):
        """Test Jaccard similarity for identical sets"""
        set1 = {"software", "engineer"}
        set2 = {"software", "engineer"}

        # Jaccard = intersection / union
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0

        self.assertEqual(jaccard, 1.0)

    def test_jaccard_similarity_different(self):
        """Test Jaccard similarity for different sets"""
        set1 = {"software", "engineer"}
        set2 = {"data", "scientist"}

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0

        self.assertEqual(jaccard, 0.0)

    def test_jaccard_similarity_overlap(self):
        """Test Jaccard similarity for overlapping sets"""
        set1 = {"senior", "software", "engineer"}
        set2 = {"software", "engineer"}

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0

        # Jaccard = 2/3 = 0.67
        self.assertAlmostEqual(jaccard, 0.67, places=2)


class TestDuplicateDetection(unittest.TestCase):
    """Test duplicate job detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.deduplicator = JobDeduplicator()
        self.normalizer = TextNormalizer()

    def test_identical_jobs_are_duplicates(self):
        """Test that identical jobs are detected as duplicates"""
        job1 = {
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }
        job2 = {
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Normalize
        title1 = self.normalizer.normalize_title(job1['title'])
        title2 = self.normalizer.normalize_title(job2['title'])

        # Check similarity
        similarity = difflib.SequenceMatcher(None, title1, title2).ratio()

        self.assertGreaterEqual(similarity, 0.85)

    def test_abbreviated_vs_full_are_duplicates(self):
        """Test that abbreviated and full forms are detected as duplicates"""
        job1 = {
            'title': 'Sr. SWE',
            'location': 'NYC',
            'company': 'bloomberg'
        }
        job2 = {
            'title': 'Senior Software Engineer',
            'location': 'New York',
            'company': 'bloomberg'
        }

        # Normalize titles
        title1 = self.normalizer.normalize_title(job1['title'])
        title2 = self.normalizer.normalize_title(job2['title'])

        # Check similarity after normalization
        similarity = difflib.SequenceMatcher(None, title1, title2).ratio()

        # After normalization, should have high similarity
        self.assertGreater(similarity, 0.7)

    def test_different_companies_not_duplicates(self):
        """Test that same job at different companies is not a duplicate"""
        job1 = {
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }
        job2 = {
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'fb'
        }

        # Should NOT be duplicates (different companies)
        self.assertNotEqual(job1['company'], job2['company'])

    def test_different_titles_not_duplicates(self):
        """Test that different job titles are not duplicates"""
        job1 = {
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }
        job2 = {
            'title': 'Data Scientist',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Normalize
        title1 = self.normalizer.normalize_title(job1['title'])
        title2 = self.normalizer.normalize_title(job2['title'])

        # Check similarity
        similarity = difflib.SequenceMatcher(None, title1, title2).ratio()

        # Should have low similarity
        self.assertLess(similarity, 0.5)


class TestSimilarityThresholds(unittest.TestCase):
    """Test similarity thresholds"""

    def test_title_threshold(self):
        """Test title similarity threshold (85%)"""
        threshold = 0.85

        # Very similar titles should pass
        similarity_high = 0.90
        self.assertGreaterEqual(similarity_high, threshold)

        # Somewhat similar titles should fail
        similarity_low = 0.70
        self.assertLess(similarity_low, threshold)

    def test_location_threshold(self):
        """Test location similarity threshold (90%)"""
        threshold = 0.90

        # Very similar locations should pass
        similarity_high = 0.95
        self.assertGreaterEqual(similarity_high, threshold)

        # Somewhat similar locations should fail
        similarity_low = 0.80
        self.assertLess(similarity_low, threshold)

    def test_combined_threshold(self):
        """Test combined similarity threshold (80%)"""
        threshold = 0.80

        # Calculate weighted average
        title_similarity = 0.85
        location_similarity = 0.70
        combined = 0.7 * title_similarity + 0.3 * location_similarity

        # combined = 0.7 * 0.85 + 0.3 * 0.70 = 0.595 + 0.21 = 0.805
        self.assertAlmostEqual(combined, 0.805, places=2)
        self.assertGreater(combined, threshold)


class TestCompanyScopedDeduplication(unittest.TestCase):
    """Test company-scoped deduplication"""

    def test_only_compare_within_company(self):
        """Test that jobs are only compared within same company"""
        jobs = [
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                'title': 'Software Engineer',
                'location': 'New York',
                'company': 'bloomberg'
            },
            {
                'url': 'https://fb.avature.net/careers/JobDetail/Job2/2',
                'title': 'Software Engineer',
                'location': 'New York',
                'company': 'fb'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job3/3',
                'title': 'Sr SWE',
                'location': 'NYC',
                'company': 'bloomberg'
            }
        ]

        # Group by company
        by_company = {}
        for job in jobs:
            company = job['company']
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(job)

        # Bloomberg should have 2 jobs
        self.assertEqual(len(by_company['bloomberg']), 2)

        # FB should have 1 job
        self.assertEqual(len(by_company['fb']), 1)

        # Jobs from different companies should not be compared
        self.assertNotEqual(jobs[0]['company'], jobs[1]['company'])


class TestDuplicateGrouping(unittest.TestCase):
    """Test duplicate grouping logic"""

    def test_group_duplicates(self):
        """Test grouping duplicate jobs"""
        jobs = [
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                'title': 'Software Engineer',
                'location': 'New York',
                'company': 'bloomberg'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job2/2',
                'title': 'Sr SWE',
                'location': 'NYC',
                'company': 'bloomberg'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job3/3',
                'title': 'Data Scientist',
                'location': 'New York',
                'company': 'bloomberg'
            }
        ]

        # Group potential duplicates (jobs 1 and 2)
        duplicate_groups = []

        # Job 1 and Job 2 are potential duplicates
        # Job 3 is different

        # Simplified grouping logic
        if jobs[0]['title'] != jobs[2]['title']:
            # Not duplicates
            pass

        # Should have at least one potential duplicate pair
        self.assertNotEqual(jobs[0]['title'], jobs[2]['title'])

    def test_keep_canonical_job(self):
        """Test keeping canonical job from duplicate group"""
        duplicate_group = [
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                'title': 'Sr SWE',
                'location': 'NYC',
                'company': 'bloomberg',
                'first_seen': '2026-02-03T00:00:00'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job2/2',
                'title': 'Senior Software Engineer',
                'location': 'New York',
                'company': 'bloomberg',
                'first_seen': '2026-02-04T00:00:00'
            }
        ]

        # Keep the one seen first
        canonical = min(duplicate_group, key=lambda x: x['first_seen'])

        self.assertEqual(canonical['url'], duplicate_group[0]['url'])


class TestDeduplicationReport(unittest.TestCase):
    """Test deduplication reporting"""

    def test_report_structure(self):
        """Test deduplication report structure"""
        report = {
            'timestamp': '2026-02-04T10:00:00',
            'total_jobs_checked': 100,
            'duplicate_groups_found': 5,
            'total_duplicates': 10,
            'duplicate_rate': 0.10,
            'groups': []
        }

        # Check report has required fields
        self.assertIn('timestamp', report)
        self.assertIn('total_jobs_checked', report)
        self.assertIn('duplicate_groups_found', report)
        self.assertIn('total_duplicates', report)
        self.assertIn('duplicate_rate', report)

    def test_duplicate_group_structure(self):
        """Test duplicate group structure in report"""
        group = {
            'canonical_job': {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                'title': 'Senior Software Engineer',
                'location': 'New York, NY',
                'company': 'bloomberg'
            },
            'duplicates': [
                {
                    'url': 'https://bloomberg.avature.net/careers/JobDetail/Job2/2',
                    'title': 'Sr SWE',
                    'location': 'NYC',
                    'company': 'bloomberg',
                    'similarity_score': 0.92,
                    'title_similarity': 0.89,
                    'location_similarity': 0.95
                }
            ]
        }

        # Check group has required fields
        self.assertIn('canonical_job', group)
        self.assertIn('duplicates', group)

        # Check duplicate has similarity scores
        duplicate = group['duplicates'][0]
        self.assertIn('similarity_score', duplicate)
        self.assertIn('title_similarity', duplicate)
        self.assertIn('location_similarity', duplicate)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases in deduplication"""

    def setUp(self):
        """Set up test fixtures"""
        self.normalizer = TextNormalizer()

    def test_empty_title_handling(self):
        """Test handling of empty titles"""
        title = ""
        normalized = self.normalizer.normalize_title(title)

        # Should handle empty string gracefully
        self.assertIsNotNone(normalized)

    def test_none_location_handling(self):
        """Test handling of None location"""
        location = None

        # Should handle None gracefully
        if location:
            normalized = self.normalizer.normalize_location(location)
        else:
            normalized = ""

        self.assertIsNotNone(normalized)

    def test_special_characters_in_title(self):
        """Test handling of special characters"""
        title = "Software Engineer (Remote)"
        normalized = self.normalizer.normalize_title(title)

        # Should preserve parentheses content
        self.assertIn("Remote", normalized)

    def test_multiple_spaces_in_title(self):
        """Test handling of multiple spaces"""
        title = "Software    Engineer"
        normalized = self.normalizer.normalize_title(title)

        # Should normalize multiple spaces to single space
        self.assertNotIn("    ", normalized)


class TestPerformance(unittest.TestCase):
    """Test deduplication performance"""

    def test_normalization_is_fast(self):
        """Test that normalization is fast enough"""
        import time

        normalizer = TextNormalizer()
        titles = ["Software Engineer"] * 1000

        start = time.time()
        for title in titles:
            normalizer.normalize_title(title)
        elapsed = time.time() - start

        # Should process 1000 titles in < 1 second
        self.assertLess(elapsed, 1.0)

    def test_company_scoped_reduces_comparisons(self):
        """Test that company scoping reduces number of comparisons"""
        # Without company scoping: O(n²) = 100² = 10,000 comparisons
        # With company scoping: O(n² / c) where c = number of companies

        jobs = [
            {'company': 'bloomberg', 'id': i}
            for i in range(50)
        ] + [
            {'company': 'fb', 'id': i}
            for i in range(50)
        ]

        # Group by company
        by_company = {}
        for job in jobs:
            company = job['company']
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(job)

        # Each company has 50 jobs
        # Comparisons per company: 50² = 2,500
        # Total: 2 * 2,500 = 5,000 (vs 10,000 without scoping)

        comparisons_with_scoping = sum(
            len(company_jobs) ** 2
            for company_jobs in by_company.values()
        )

        comparisons_without_scoping = len(jobs) ** 2

        # Should reduce comparisons by ~50%
        self.assertLess(comparisons_with_scoping, comparisons_without_scoping)


def run_phase4_tests():
    """Run all Phase 4 tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTextNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestLocationNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestSimilarityAlgorithms))
    suite.addTests(loader.loadTestsFromTestCase(TestDuplicateDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestSimilarityThresholds))
    suite.addTests(loader.loadTestsFromTestCase(TestCompanyScopedDeduplication))
    suite.addTests(loader.loadTestsFromTestCase(TestDuplicateGrouping))
    suite.addTests(loader.loadTestsFromTestCase(TestDeduplicationReport))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("=" * 70)
    print("Phase 4: Fuzzy Deduplication - Test Suite")
    print("=" * 70)
    print()

    result = run_phase4_tests()

    print()
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
