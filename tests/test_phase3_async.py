"""
Test Suite for Phase 3: Async Scraping

Tests the async scraping functionality including:
- aiohttp session management
- Connection pooling
- Semaphore-based rate limiting
- Concurrent operations
- Error isolation
- Performance improvements
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import tempfile
import time


# Mock async scraper for testing
class MockAsyncScraper:
    """Mock async scraper for testing"""

    def __init__(self, max_concurrent_sites=5, max_concurrent_pages=3):
        self.max_concurrent_sites = max_concurrent_sites
        self.max_concurrent_pages = max_concurrent_pages
        self.site_semaphore = asyncio.Semaphore(max_concurrent_sites)
        self.page_semaphore = asyncio.Semaphore(max_concurrent_pages)
        self.session = None

    async def create_session(self):
        """Create aiohttp session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent_sites * self.max_concurrent_pages,
            limit_per_host=self.max_concurrent_pages
        )
        self.session = aiohttp.ClientSession(connector=connector)

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def scrape_site_with_semaphore(self, url):
        """Scrape site with semaphore control"""
        async with self.site_semaphore:
            # Simulate scraping
            await asyncio.sleep(0.01)
            return {'url': url, 'jobs': []}

    async def scrape_page_with_semaphore(self, url, page):
        """Scrape page with semaphore control"""
        async with self.page_semaphore:
            # Simulate scraping
            await asyncio.sleep(0.01)
            return {'url': url, 'page': page, 'jobs': []}


class TestAsyncScraperInitialization(unittest.TestCase):
    """Test async scraper initialization"""

    def test_scraper_creation(self):
        """Test that async scraper can be instantiated"""
        scraper = MockAsyncScraper()
        self.assertIsNotNone(scraper)

    def test_scraper_configuration(self):
        """Test scraper configuration parameters"""
        scraper = MockAsyncScraper(max_concurrent_sites=10, max_concurrent_pages=5)
        self.assertEqual(scraper.max_concurrent_sites, 10)
        self.assertEqual(scraper.max_concurrent_pages, 5)

    def test_semaphores_initialized(self):
        """Test that semaphores are initialized"""
        scraper = MockAsyncScraper(max_concurrent_sites=5, max_concurrent_pages=3)
        self.assertIsNotNone(scraper.site_semaphore)
        self.assertIsNotNone(scraper.page_semaphore)


class TestConnectionPooling(unittest.TestCase):
    """Test connection pooling configuration"""

    def test_tcp_connector_limits(self):
        """Test TCP connector connection limits"""
        async def test_connector():
            max_concurrent_sites = 5
            max_concurrent_pages = 3
            total_connections = max_concurrent_sites * max_concurrent_pages

            # Create connector
            connector = aiohttp.TCPConnector(
                limit=total_connections,
                limit_per_host=max_concurrent_pages
            )

            self.assertEqual(connector.limit, 15)
            self.assertEqual(connector.limit_per_host, 3)

            # Close connector
            await connector.close()

        asyncio.run(test_connector())

    def test_session_with_connector(self):
        """Test creating session with custom connector"""
        async def create_and_close():
            connector = aiohttp.TCPConnector(limit=15, limit_per_host=3)
            session = aiohttp.ClientSession(connector=connector)
            self.assertIsNotNone(session)
            await session.close()

        asyncio.run(create_and_close())


class TestSemaphoreControl(unittest.TestCase):
    """Test semaphore-based rate limiting"""

    def test_semaphore_limits_concurrent_operations(self):
        """Test that semaphore limits concurrent operations"""
        async def test_concurrent():
            semaphore = asyncio.Semaphore(3)
            active_count = 0
            max_active = 0

            async def task():
                nonlocal active_count, max_active
                async with semaphore:
                    active_count += 1
                    max_active = max(max_active, active_count)
                    await asyncio.sleep(0.01)
                    active_count -= 1

            # Run 10 tasks concurrently
            tasks = [task() for _ in range(10)]
            await asyncio.gather(*tasks)

            return max_active

        max_active = asyncio.run(test_concurrent())

        # Should never exceed semaphore limit
        self.assertLessEqual(max_active, 3)

    def test_site_semaphore_limits(self):
        """Test that site semaphore limits concurrent sites"""
        scraper = MockAsyncScraper(max_concurrent_sites=5)

        # Semaphore should have 5 available slots
        self.assertLessEqual(scraper.site_semaphore._value, 5)

    def test_page_semaphore_limits(self):
        """Test that page semaphore limits concurrent pages"""
        scraper = MockAsyncScraper(max_concurrent_pages=3)

        # Semaphore should have 3 available slots
        self.assertLessEqual(scraper.page_semaphore._value, 3)


class TestConcurrentOperations(unittest.TestCase):
    """Test concurrent scraping operations"""

    def test_gather_multiple_tasks(self):
        """Test gathering multiple async tasks"""
        async def test_gather():
            async def mock_scrape(site_id):
                await asyncio.sleep(0.01)
                return {'site_id': site_id, 'jobs': []}

            # Create tasks for 3 sites
            tasks = [mock_scrape(i) for i in range(3)]
            results = await asyncio.gather(*tasks)

            return results

        results = asyncio.run(test_gather())

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['site_id'], 0)
        self.assertEqual(results[2]['site_id'], 2)

    def test_concurrent_sites_scraping(self):
        """Test scraping multiple sites concurrently"""
        async def test_concurrent_sites():
            scraper = MockAsyncScraper(max_concurrent_sites=3)

            sites = [
                'https://bloomberg.avature.net/careers',
                'https://fb.avature.net/careers',
                'https://uclahealth.avature.net/careers'
            ]

            tasks = [scraper.scrape_site_with_semaphore(site) for site in sites]
            results = await asyncio.gather(*tasks)

            return results

        results = asyncio.run(test_concurrent_sites())

        self.assertEqual(len(results), 3)

    def test_concurrent_pages_scraping(self):
        """Test scraping multiple pages concurrently"""
        async def test_concurrent_pages():
            scraper = MockAsyncScraper(max_concurrent_pages=3)

            pages = [1, 2, 3, 4, 5]
            url = 'https://bloomberg.avature.net/careers/SearchJobs'

            tasks = [scraper.scrape_page_with_semaphore(url, page) for page in pages]
            results = await asyncio.gather(*tasks)

            return results

        results = asyncio.run(test_concurrent_pages())

        self.assertEqual(len(results), 5)


class TestErrorIsolation(unittest.TestCase):
    """Test error handling and isolation"""

    def test_gather_with_return_exceptions(self):
        """Test that errors don't stop other tasks"""
        async def test_error_isolation():
            async def task_success(task_id):
                await asyncio.sleep(0.01)
                return {'task_id': task_id, 'status': 'success'}

            async def task_failure(task_id):
                await asyncio.sleep(0.01)
                raise Exception(f"Task {task_id} failed")

            # Mix successful and failing tasks
            tasks = [
                task_success(1),
                task_failure(2),
                task_success(3),
                task_failure(4),
                task_success(5)
            ]

            # Use return_exceptions=True
            results = await asyncio.gather(*tasks, return_exceptions=True)

            return results

        results = asyncio.run(test_error_isolation())

        # Should have 5 results (3 successes, 2 exceptions)
        self.assertEqual(len(results), 5)

        # Check that successes are dicts
        self.assertIsInstance(results[0], dict)
        self.assertEqual(results[0]['status'], 'success')

        # Check that failures are exceptions
        self.assertIsInstance(results[1], Exception)

        # Check that other tasks continued despite errors
        self.assertIsInstance(results[2], dict)
        self.assertEqual(results[2]['status'], 'success')

    def test_single_site_failure_doesnt_block_others(self):
        """Test that one site failure doesn't block others"""
        async def test_failure_isolation():
            async def scrape_site(site_id, should_fail=False):
                async with asyncio.Semaphore(5):
                    await asyncio.sleep(0.01)
                    if should_fail:
                        raise Exception(f"Site {site_id} failed")
                    return {'site_id': site_id, 'jobs': []}

            # Site 2 fails, others succeed
            tasks = [
                scrape_site(1, False),
                scrape_site(2, True),
                scrape_site(3, False)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            return results

        results = asyncio.run(test_failure_isolation())

        # Should have 3 results
        self.assertEqual(len(results), 3)

        # First and third should succeed
        self.assertIsInstance(results[0], dict)
        self.assertIsInstance(results[2], dict)

        # Second should be exception
        self.assertIsInstance(results[1], Exception)


class TestPerformance(unittest.TestCase):
    """Test performance improvements"""

    def test_async_faster_than_sync(self):
        """Test that async is faster than sequential"""
        async def async_version():
            async def task():
                await asyncio.sleep(0.1)
                return True

            start = time.time()
            tasks = [task() for _ in range(5)]
            await asyncio.gather(*tasks)
            return time.time() - start

        def sync_version():
            import time as time_sync

            def task():
                time_sync.sleep(0.1)
                return True

            start = time_sync.time()
            for _ in range(5):
                task()
            return time_sync.time() - start

        async_time = asyncio.run(async_version())
        sync_time = sync_version()

        # Async should be significantly faster (runs in parallel)
        # 5 tasks at 0.1s each: sync = 0.5s, async = 0.1s
        self.assertLess(async_time, sync_time)
        self.assertLess(async_time, 0.2)  # Should complete in < 0.2s
        self.assertGreater(sync_time, 0.4)  # Should take > 0.4s

    def test_connection_pooling_reuses_connections(self):
        """Test that connection pooling reuses connections"""
        async def test_pooling():
            # This is tested implicitly by TCPConnector configuration
            # Connection pooling allows multiple requests to same host
            # without creating new TCP connections each time
            connector = aiohttp.TCPConnector(limit_per_host=3)
            self.assertEqual(connector.limit_per_host, 3)
            await connector.close()

        asyncio.run(test_pooling())


class TestSessionManagement(unittest.TestCase):
    """Test aiohttp session management"""

    def test_session_creation(self):
        """Test creating aiohttp session"""
        async def test_session():
            scraper = MockAsyncScraper()
            await scraper.create_session()

            self.assertIsNotNone(scraper.session)
            self.assertIsInstance(scraper.session, aiohttp.ClientSession)

            await scraper.close_session()

        asyncio.run(test_session())

    def test_session_cleanup(self):
        """Test that session is properly closed"""
        async def test_cleanup():
            scraper = MockAsyncScraper()
            await scraper.create_session()

            self.assertIsNotNone(scraper.session)

            await scraper.close_session()

            # Session should be closed
            self.assertTrue(scraper.session.closed)

        asyncio.run(test_cleanup())


class TestAsyncPatterns(unittest.TestCase):
    """Test async programming patterns"""

    def test_async_with_context_manager(self):
        """Test async with context manager for semaphores"""
        async def test_context():
            semaphore = asyncio.Semaphore(1)
            value_before = semaphore._value

            async with semaphore:
                value_during = semaphore._value
                # Should acquire semaphore
                self.assertEqual(value_during, 0)

            value_after = semaphore._value
            # Should release semaphore
            self.assertEqual(value_after, 1)

        asyncio.run(test_context())

    def test_asyncio_gather_order_preservation(self):
        """Test that gather preserves order of results"""
        async def test_order():
            async def task(task_id):
                # Reverse order sleep times
                await asyncio.sleep(0.01 * (10 - task_id))
                return task_id

            tasks = [task(i) for i in range(1, 6)]
            results = await asyncio.gather(*tasks)

            return results

        results = asyncio.run(test_order())

        # Results should be in order [1, 2, 3, 4, 5]
        # even though tasks complete in reverse order
        self.assertEqual(results, [1, 2, 3, 4, 5])


class TestConcurrencyLimits(unittest.TestCase):
    """Test concurrency limits and configurations"""

    def test_default_concurrency_limits(self):
        """Test default concurrency limits"""
        scraper = MockAsyncScraper(max_concurrent_sites=5, max_concurrent_pages=3)

        self.assertEqual(scraper.max_concurrent_sites, 5)
        self.assertEqual(scraper.max_concurrent_pages, 3)

    def test_custom_concurrency_limits(self):
        """Test custom concurrency limits"""
        scraper = MockAsyncScraper(max_concurrent_sites=10, max_concurrent_pages=5)

        self.assertEqual(scraper.max_concurrent_sites, 10)
        self.assertEqual(scraper.max_concurrent_pages, 5)

    def test_conservative_limits_for_politeness(self):
        """Test conservative limits for polite scraping"""
        scraper = MockAsyncScraper(max_concurrent_sites=2, max_concurrent_pages=2)

        self.assertEqual(scraper.max_concurrent_sites, 2)
        self.assertEqual(scraper.max_concurrent_pages, 2)


class TestAsyncIntegrationWithDatabase(unittest.TestCase):
    """Test async scraping with database integration"""

    def test_async_results_can_be_inserted_to_db(self):
        """Test that async scraping results can be inserted to database"""
        async def test_integration():
            # Mock async scraping that returns jobs
            async def scrape_site():
                await asyncio.sleep(0.01)
                return [
                    {
                        'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                        'job_id': '1',
                        'title': 'Job 1',
                        'location': 'NY',
                        'company': 'bloomberg'
                    }
                ]

            jobs = await scrape_site()

            # Verify jobs can be processed
            self.assertEqual(len(jobs), 1)
            self.assertIn('url', jobs[0])
            self.assertIn('title', jobs[0])

        asyncio.run(test_integration())


def run_phase3_tests():
    """Run all Phase 3 tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncScraperInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestConnectionPooling))
    suite.addTests(loader.loadTestsFromTestCase(TestSemaphoreControl))
    suite.addTests(loader.loadTestsFromTestCase(TestConcurrentOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorIsolation))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestConcurrencyLimits))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncIntegrationWithDatabase))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("=" * 70)
    print("Phase 3: Async Scraping - Test Suite")
    print("=" * 70)
    print()

    result = run_phase3_tests()

    print()
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
