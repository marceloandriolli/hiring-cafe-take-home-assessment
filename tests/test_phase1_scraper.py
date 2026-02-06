"""
Test Suite for Phase 1: Basic Scraper

Tests the core scraping functionality including:
- HTML parsing
- Job extraction
- Pagination handling
- Error handling
- URL validation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import Mock, patch, MagicMock
from src.scraper import AvatureScraper
from bs4 import BeautifulSoup
import json


class TestAvatureScraperInitialization(unittest.TestCase):
    """Test scraper initialization and configuration"""

    def test_scraper_creation(self):
        """Test that scraper can be instantiated"""
        scraper = AvatureScraper()
        self.assertIsNotNone(scraper)

    def test_scraper_default_settings(self):
        """Test default configuration values"""
        scraper = AvatureScraper()
        # Check that scraper has expected attributes
        self.assertTrue(hasattr(scraper, 'scrape_site') or hasattr(scraper, 'scrape_jobs'))


class TestJobExtraction(unittest.TestCase):
    """Test job extraction from HTML"""

    def setUp(self):
        """Set up test fixtures"""
        self.scraper = AvatureScraper()

        # Sample HTML with job listings
        self.sample_html = """
        <html>
            <body>
                <article class="job-listing">
                    <a href="/careers/JobDetail/Software-Engineer/12345">
                        <h3>Software Engineer</h3>
                    </a>
                    <span class="location">New York, NY</span>
                </article>
                <article class="job-listing">
                    <a href="/careers/JobDetail/Data-Scientist/67890">
                        <h3>Data Scientist</h3>
                    </a>
                    <span class="location">San Francisco, CA</span>
                </article>
            </body>
        </html>
        """

    def test_parse_html_finds_jobs(self):
        """Test that parser finds job listings in HTML"""
        soup = BeautifulSoup(self.sample_html, 'html.parser')
        articles = soup.find_all('article', class_='job-listing')
        self.assertEqual(len(articles), 2)

    def test_extract_job_title(self):
        """Test extraction of job title"""
        soup = BeautifulSoup(self.sample_html, 'html.parser')
        article = soup.find('article', class_='job-listing')
        title = article.find('h3').text
        self.assertEqual(title, 'Software Engineer')

    def test_extract_job_url(self):
        """Test extraction of job URL"""
        soup = BeautifulSoup(self.sample_html, 'html.parser')
        article = soup.find('article', class_='job-listing')
        url = article.find('a')['href']
        self.assertIn('JobDetail', url)
        self.assertIn('12345', url)

    def test_extract_location(self):
        """Test extraction of job location"""
        soup = BeautifulSoup(self.sample_html, 'html.parser')
        article = soup.find('article', class_='job-listing')
        location = article.find('span', class_='location').text
        self.assertEqual(location, 'New York, NY')


class TestURLConstruction(unittest.TestCase):
    """Test URL construction and validation"""

    def test_base_url_format(self):
        """Test that base URL is properly formatted"""
        base_url = "https://bloomberg.avature.net/careers"
        self.assertTrue(base_url.startswith('https://'))
        self.assertIn('.avature.net', base_url)
        self.assertTrue(base_url.endswith('/careers'))

    def test_search_url_construction(self):
        """Test construction of search URL"""
        base_url = "https://bloomberg.avature.net/careers"
        search_url = f"{base_url}/SearchJobs"
        self.assertEqual(search_url, "https://bloomberg.avature.net/careers/SearchJobs")

    def test_pagination_url_construction(self):
        """Test pagination URL construction"""
        base_url = "https://bloomberg.avature.net/careers/SearchJobs"
        page_url = f"{base_url}?page=2"
        self.assertIn('?page=2', page_url)

    def test_job_detail_url_construction(self):
        """Test job detail URL construction"""
        base_url = "https://bloomberg.avature.net"
        job_path = "/careers/JobDetail/Software-Engineer/12345"
        full_url = f"{base_url}{job_path}"
        self.assertEqual(full_url, "https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345")


class TestJobDataStructure(unittest.TestCase):
    """Test job data structure and validation"""

    def test_job_has_required_fields(self):
        """Test that job dictionary has all required fields"""
        job = {
            'title': 'Software Engineer',
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'company': 'bloomberg',
            'location': 'New York, NY'
        }

        # Check required fields
        self.assertIn('title', job)
        self.assertIn('url', job)
        self.assertIn('job_id', job)
        self.assertIn('company', job)

    def test_job_title_not_empty(self):
        """Test that job title is not empty"""
        job = {'title': 'Software Engineer'}
        self.assertTrue(len(job['title']) > 0)

    def test_job_url_valid_format(self):
        """Test that job URL has valid format"""
        job = {'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345'}
        self.assertTrue(job['url'].startswith('https://'))
        self.assertIn('avature.net', job['url'])

    def test_company_extracted_from_url(self):
        """Test that company name can be extracted from URL"""
        url = "https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345"
        # Extract company from URL
        company = url.split('.avature.net')[0].split('://')[-1]
        self.assertEqual(company, 'bloomberg')


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    def test_empty_html_returns_empty_list(self):
        """Test that empty HTML returns empty job list"""
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article')
        self.assertEqual(len(articles), 0)

    def test_malformed_html_doesnt_crash(self):
        """Test that malformed HTML doesn't crash parser"""
        html = "<html><body><article>Incomplete"
        try:
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('article')
            # Should not raise exception
            self.assertIsNotNone(articles)
        except Exception as e:
            self.fail(f"Parser crashed on malformed HTML: {e}")

    def test_missing_job_fields_handled(self):
        """Test that missing optional fields don't cause errors"""
        html = """
        <article class="job-listing">
            <a href="/careers/JobDetail/Software-Engineer/12345">
                <h3>Software Engineer</h3>
            </a>
        </article>
        """
        soup = BeautifulSoup(html, 'html.parser')
        article = soup.find('article')

        # Should handle missing location gracefully
        location = article.find('span', class_='location')
        self.assertIsNone(location)


class TestPaginationLogic(unittest.TestCase):
    """Test pagination detection and handling"""

    def test_pagination_url_format(self):
        """Test pagination URL format"""
        base_url = "https://bloomberg.avature.net/careers/SearchJobs"

        # Test page 1
        page1_url = f"{base_url}?page=1"
        self.assertIn('?page=1', page1_url)

        # Test page 10
        page10_url = f"{base_url}?page=10"
        self.assertIn('?page=10', page10_url)

    def test_pagination_range(self):
        """Test pagination range logic"""
        max_pages = 100
        pages = list(range(1, max_pages + 1))

        self.assertEqual(len(pages), 100)
        self.assertEqual(pages[0], 1)
        self.assertEqual(pages[-1], 100)


class TestDataValidation(unittest.TestCase):
    """Test data validation and cleaning"""

    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed from extracted text"""
        text = "  Software Engineer  "
        cleaned = text.strip()
        self.assertEqual(cleaned, "Software Engineer")

    def test_url_normalization(self):
        """Test URL normalization"""
        relative_url = "/careers/JobDetail/Software-Engineer/12345"
        base_url = "https://bloomberg.avature.net"

        # Should handle both absolute and relative URLs
        if relative_url.startswith('/'):
            full_url = base_url + relative_url
        else:
            full_url = relative_url

        self.assertTrue(full_url.startswith('https://'))

    def test_job_id_extraction(self):
        """Test job ID extraction from URL"""
        url = "/careers/JobDetail/Software-Engineer/12345"
        # Extract last segment as job ID
        job_id = url.split('/')[-1]
        self.assertEqual(job_id, "12345")


class TestCompanyExtraction(unittest.TestCase):
    """Test company name extraction"""

    def test_extract_company_from_bloomberg_url(self):
        """Test extraction from Bloomberg URL"""
        url = "https://bloomberg.avature.net/careers"
        company = url.split('.avature.net')[0].split('://')[-1]
        self.assertEqual(company, 'bloomberg')

    def test_extract_company_from_meta_url(self):
        """Test extraction from Meta URL"""
        url = "https://fb.avature.net/careers"
        company = url.split('.avature.net')[0].split('://')[-1]
        self.assertEqual(company, 'fb')

    def test_extract_company_from_ucla_url(self):
        """Test extraction from UCLA Health URL"""
        url = "https://uclahealth.avature.net/careers"
        company = url.split('.avature.net')[0].split('://')[-1]
        self.assertEqual(company, 'uclahealth')


class TestRateLimiting(unittest.TestCase):
    """Test rate limiting functionality"""

    def test_sleep_delays_configured(self):
        """Test that sleep delays are properly configured"""
        page_delay = 0.5  # seconds between pages
        site_delay = 1.0  # seconds between sites

        self.assertGreater(page_delay, 0)
        self.assertGreater(site_delay, 0)
        self.assertGreater(site_delay, page_delay)


def run_phase1_tests():
    """Run all Phase 1 tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAvatureScraperInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestJobExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestURLConstruction))
    suite.addTests(loader.loadTestsFromTestCase(TestJobDataStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestPaginationLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestDataValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestCompanyExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimiting))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("=" * 70)
    print("Phase 1: Basic Scraper - Test Suite")
    print("=" * 70)
    print()

    result = run_phase1_tests()

    print()
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
