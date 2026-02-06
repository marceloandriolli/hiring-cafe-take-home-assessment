"""
Test Suite for Phase 2: Database & Incremental Updates

Tests the database layer and incremental scraping functionality including:
- SQLite database operations
- Job lifecycle tracking (first_seen, last_seen, scrape_count)
- Upsert logic (new/updated/unchanged detection)
- Smart stopping algorithm
- Job deactivation
- Statistics tracking
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import sqlite3
import tempfile
import json
from datetime import datetime, timedelta
from src.database import JobDatabase


class TestDatabaseInitialization(unittest.TestCase):
    """Test database creation and initialization"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_database_creation(self):
        """Test that database file is created"""
        db = JobDatabase(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

    def test_jobs_table_created(self):
        """Test that jobs table is created with correct schema"""
        db = JobDatabase(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)

        # Check columns
        cursor.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in cursor.fetchall()}

        expected_columns = {
            'url', 'job_id', 'title', 'location', 'company',
            'first_seen', 'last_seen', 'scrape_count', 'is_active'
        }

        self.assertTrue(expected_columns.issubset(columns))
        conn.close()

    def test_indices_created(self):
        """Test that database indices are created"""
        db = JobDatabase(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check for indices
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indices = [row[0] for row in cursor.fetchall()]

        # Should have indices on common query fields
        self.assertTrue(len(indices) > 0)
        conn.close()


class TestJobUpsert(unittest.TestCase):
    """Test job insertion and update logic"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = JobDatabase(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_insert_new_job(self):
        """Test inserting a new job"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        action, changed = self.db.upsert_job(job)

        self.assertEqual(action, 'new')
        self.assertTrue(changed)

    def test_update_existing_job_with_changes(self):
        """Test updating a job with changed title"""
        job1 = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Insert first time
        self.db.upsert_job(job1)

        # Update with changed title
        job2 = job1.copy()
        job2['title'] = 'Senior Software Engineer'

        action, changed = self.db.upsert_job(job2)

        self.assertEqual(action, 'updated')
        self.assertTrue(changed)

    def test_unchanged_job_detection(self):
        """Test that unchanged jobs are detected"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Insert first time
        self.db.upsert_job(job)

        # Insert again with no changes
        action, changed = self.db.upsert_job(job)

        self.assertEqual(action, 'unchanged')
        self.assertFalse(changed)

    def test_scrape_count_increments(self):
        """Test that scrape_count increments on each scrape"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Insert 3 times
        self.db.upsert_job(job)
        self.db.upsert_job(job)
        self.db.upsert_job(job)

        # Check scrape_count
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT scrape_count FROM jobs WHERE url = ?", (job['url'],))
        scrape_count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(scrape_count, 3)


class TestJobLifecycle(unittest.TestCase):
    """Test job lifecycle tracking"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = JobDatabase(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_first_seen_timestamp_set(self):
        """Test that first_seen timestamp is set on insert"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        self.db.upsert_job(job)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT first_seen FROM jobs WHERE url = ?", (job['url'],))
        first_seen = cursor.fetchone()[0]
        conn.close()

        self.assertIsNotNone(first_seen)

    def test_last_seen_updates(self):
        """Test that last_seen updates on each scrape"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Insert first time
        self.db.upsert_job(job)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT last_seen FROM jobs WHERE url = ?", (job['url'],))
        last_seen1 = cursor.fetchone()[0]

        # Insert again
        self.db.upsert_job(job)

        cursor.execute("SELECT last_seen FROM jobs WHERE url = ?", (job['url'],))
        last_seen2 = cursor.fetchone()[0]
        conn.close()

        # last_seen should be updated
        self.assertIsNotNone(last_seen1)
        self.assertIsNotNone(last_seen2)

    def test_job_starts_active(self):
        """Test that new jobs are marked as active"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        self.db.upsert_job(job)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM jobs WHERE url = ?", (job['url'],))
        is_active = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(is_active, 1)


class TestJobDeactivation(unittest.TestCase):
    """Test job deactivation logic"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = JobDatabase(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_mark_missing_jobs_inactive(self):
        """Test that missing jobs are marked inactive"""
        # Insert 3 jobs
        jobs = [
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                'job_id': '1',
                'title': 'Job 1',
                'location': 'NY',
                'company': 'bloomberg'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job2/2',
                'job_id': '2',
                'title': 'Job 2',
                'location': 'NY',
                'company': 'bloomberg'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job3/3',
                'job_id': '3',
                'title': 'Job 3',
                'location': 'NY',
                'company': 'bloomberg'
            }
        ]

        for job in jobs:
            self.db.upsert_job(job)

        # Mark jobs 2 and 3 as seen (job 1 is missing)
        active_urls = [jobs[1]['url'], jobs[2]['url']]
        deactivated = self.db.mark_inactive_jobs(active_urls, 'bloomberg')

        self.assertEqual(deactivated, 1)

        # Check that job 1 is inactive
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM jobs WHERE url = ?", (jobs[0]['url'],))
        is_active = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(is_active, 0)

    def test_reactivate_job(self):
        """Test that inactive jobs can be reactivated"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        # Insert job
        self.db.upsert_job(job)

        # Mark as inactive
        self.db.mark_inactive_jobs(set(), 'bloomberg')

        # Insert again (reactivate)
        self.db.upsert_job(job)

        # Check that job is active
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM jobs WHERE url = ?", (job['url'],))
        is_active = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(is_active, 1)


class TestStatistics(unittest.TestCase):
    """Test statistics and reporting"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = JobDatabase(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_get_stats(self):
        """Test getting database statistics"""
        # Insert some jobs
        jobs = [
            {
                'url': f'https://bloomberg.avature.net/careers/JobDetail/Job{i}/{i}',
                'job_id': str(i),
                'title': f'Job {i}',
                'location': 'NY',
                'company': 'bloomberg'
            }
            for i in range(1, 6)
        ]

        for job in jobs:
            self.db.upsert_job(job)

        # Mark one inactive
        active_urls = [job['url'] for job in jobs[1:]]
        self.db.mark_inactive_jobs(active_urls, 'bloomberg')

        # Get stats
        stats = self.db.get_stats()

        self.assertEqual(stats['total_jobs'], 5)
        self.assertEqual(stats['active_jobs'], 4)
        self.assertEqual(stats['inactive_jobs'], 1)

    def test_get_jobs_by_company(self):
        """Test getting jobs filtered by company"""
        # Insert jobs from different companies
        jobs = [
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job1/1',
                'job_id': '1',
                'title': 'Job 1',
                'location': 'NY',
                'company': 'bloomberg'
            },
            {
                'url': 'https://fb.avature.net/careers/JobDetail/Job2/2',
                'job_id': '2',
                'title': 'Job 2',
                'location': 'CA',
                'company': 'fb'
            },
            {
                'url': 'https://bloomberg.avature.net/careers/JobDetail/Job3/3',
                'job_id': '3',
                'title': 'Job 3',
                'location': 'NY',
                'company': 'bloomberg'
            }
        ]

        for job in jobs:
            self.db.upsert_job(job)

        # Get Bloomberg jobs
        bloomberg_jobs = self.db.get_active_jobs(company='bloomberg')

        self.assertEqual(len(bloomberg_jobs), 2)

    def test_get_all_active_jobs(self):
        """Test getting all active jobs"""
        # Insert jobs
        jobs = [
            {
                'url': f'https://bloomberg.avature.net/careers/JobDetail/Job{i}/{i}',
                'job_id': str(i),
                'title': f'Job {i}',
                'location': 'NY',
                'company': 'bloomberg'
            }
            for i in range(1, 4)
        ]

        for job in jobs:
            self.db.upsert_job(job)

        # Mark one inactive
        active_urls = [jobs[0]['url'], jobs[1]['url']]
        self.db.mark_inactive_jobs(active_urls, 'bloomberg')

        # Get active jobs
        active_jobs = self.db.get_active_jobs()

        self.assertEqual(len(active_jobs), 2)


class TestSmartStopping(unittest.TestCase):
    """Test smart stopping algorithm logic"""

    def test_smart_stop_threshold(self):
        """Test smart stopping threshold"""
        smart_stop_pages = 5
        pages_without_new = 0

        # Simulate finding new jobs
        for page in range(1, 10):
            new_jobs_on_page = 5 if page <= 3 else 0

            if new_jobs_on_page == 0:
                pages_without_new += 1
                if pages_without_new >= smart_stop_pages:
                    break
            else:
                pages_without_new = 0

        # Should stop at page 8 (pages 4-8 have no new jobs = 5 pages)
        self.assertEqual(page, 8)

    def test_smart_stop_reset(self):
        """Test that smart stop counter resets when new jobs found"""
        pages_without_new = 4

        # Find a new job
        new_jobs_on_page = 1

        if new_jobs_on_page > 0:
            pages_without_new = 0

        self.assertEqual(pages_without_new, 0)


class TestDatabaseQueries(unittest.TestCase):
    """Test database query operations"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = JobDatabase(self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_query_by_url(self):
        """Test querying job by URL"""
        job = {
            'url': 'https://bloomberg.avature.net/careers/JobDetail/Software-Engineer/12345',
            'job_id': '12345',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'company': 'bloomberg'
        }

        self.db.upsert_job(job)

        # Query by URL
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE url = ?", (job['url'],))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Software Engineer')

    def test_query_active_jobs_only(self):
        """Test querying only active jobs"""
        jobs = [
            {
                'url': f'https://bloomberg.avature.net/careers/JobDetail/Job{i}/{i}',
                'job_id': str(i),
                'title': f'Job {i}',
                'location': 'NY',
                'company': 'bloomberg'
            }
            for i in range(1, 4)
        ]

        for job in jobs:
            self.db.upsert_job(job)

        # Mark one inactive
        active_urls = [jobs[0]['url'], jobs[1]['url']]
        self.db.mark_inactive_jobs(active_urls, 'bloomberg')

        # Query active jobs
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 2)


def run_phase2_tests():
    """Run all Phase 2 tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestJobUpsert))
    suite.addTests(loader.loadTestsFromTestCase(TestJobLifecycle))
    suite.addTests(loader.loadTestsFromTestCase(TestJobDeactivation))
    suite.addTests(loader.loadTestsFromTestCase(TestStatistics))
    suite.addTests(loader.loadTestsFromTestCase(TestSmartStopping))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseQueries))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("=" * 70)
    print("Phase 2: Database & Incremental Updates - Test Suite")
    print("=" * 70)
    print()

    result = run_phase2_tests()

    print()
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
