#!/usr/bin/env python3
"""
Database layer for tracking jobs and scrape runs.
Enables incremental updates and historical tracking.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class JobDatabase:
    """SQLite database for job tracking and incremental updates."""

    def __init__(self, db_path: str = "data/jobs.db"):
        """Initialize database connection and create tables if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Jobs table - tracks individual job postings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                job_id TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                scrape_count INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active)
        """)

        # Scrape runs table - tracks each scraping session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                sites_scraped INTEGER DEFAULT 0,
                jobs_found INTEGER DEFAULT 0,
                jobs_new INTEGER DEFAULT 0,
                jobs_updated INTEGER DEFAULT 0,
                jobs_deactivated INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_message TEXT
            )
        """)

        self.conn.commit()

    def start_scrape_run(self) -> int:
        """Start a new scrape run and return its ID.

        Returns:
            The ID of the newly created scrape run
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scrape_runs (started_at, status)
            VALUES (?, 'running')
        """, (datetime.now().isoformat(),))
        self.conn.commit()
        return cursor.lastrowid

    def complete_scrape_run(self, run_id: int, stats: Dict):
        """Mark a scrape run as complete with final statistics.

        Args:
            run_id: The scrape run ID
            stats: Dictionary with keys: sites_scraped, jobs_found, jobs_new,
                   jobs_updated, jobs_deactivated, error_message (optional)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE scrape_runs
            SET completed_at = ?,
                sites_scraped = ?,
                jobs_found = ?,
                jobs_new = ?,
                jobs_updated = ?,
                jobs_deactivated = ?,
                status = ?,
                error_message = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            stats.get('sites_scraped', 0),
            stats.get('jobs_found', 0),
            stats.get('jobs_new', 0),
            stats.get('jobs_updated', 0),
            stats.get('jobs_deactivated', 0),
            stats.get('status', 'completed'),
            stats.get('error_message'),
            run_id
        ))
        self.conn.commit()

    def upsert_job(self, job: Dict) -> Tuple[str, bool]:
        """Insert or update a job in the database.

        Args:
            job: Dictionary with keys: url, company, title, location, job_id, metadata

        Returns:
            Tuple of (action, changed) where action is 'new', 'updated', or 'unchanged'
            and changed is True if the job data changed
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Check if job exists
        cursor.execute("SELECT * FROM jobs WHERE url = ?", (job['url'],))
        existing = cursor.fetchone()

        if existing is None:
            # New job - insert
            cursor.execute("""
                INSERT INTO jobs (url, company, title, location, job_id,
                                first_seen, last_seen, scrape_count, is_active, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?)
            """, (
                job['url'],
                job['company'],
                job['title'],
                job.get('location'),
                job.get('job_id'),
                now,
                now,
                json.dumps(job.get('metadata', {}))
            ))
            self.conn.commit()
            return ('new', True)
        else:
            # Existing job - check if data changed
            changed = (
                existing['title'] != job['title'] or
                existing['location'] != job.get('location') or
                existing['is_active'] != 1
            )

            # Update last_seen and scrape_count
            cursor.execute("""
                UPDATE jobs
                SET last_seen = ?,
                    scrape_count = scrape_count + 1,
                    is_active = 1,
                    title = ?,
                    location = ?,
                    job_id = ?,
                    metadata = ?
                WHERE url = ?
            """, (
                now,
                job['title'],
                job.get('location'),
                job.get('job_id'),
                json.dumps(job.get('metadata', {})),
                job['url']
            ))
            self.conn.commit()

            if changed:
                return ('updated', True)
            else:
                return ('unchanged', False)

    def mark_inactive_jobs(self, active_urls: List[str], company: str = None) -> int:
        """Mark jobs as inactive if they weren't seen in the latest scrape.

        Args:
            active_urls: List of URLs that were seen in the current scrape
            company: Optional company name to limit the scope

        Returns:
            Number of jobs marked as inactive
        """
        cursor = self.conn.cursor()

        if not active_urls:
            # If no jobs found, mark all as inactive for this company
            if company:
                cursor.execute("""
                    UPDATE jobs
                    SET is_active = 0
                    WHERE company = ? AND is_active = 1
                """, (company,))
            else:
                cursor.execute("""
                    UPDATE jobs
                    SET is_active = 0
                    WHERE is_active = 1
                """)
        else:
            # Mark jobs not in active_urls as inactive
            placeholders = ','.join('?' * len(active_urls))
            if company:
                cursor.execute(f"""
                    UPDATE jobs
                    SET is_active = 0
                    WHERE company = ? AND url NOT IN ({placeholders}) AND is_active = 1
                """, [company] + active_urls)
            else:
                cursor.execute(f"""
                    UPDATE jobs
                    SET is_active = 0
                    WHERE url NOT IN ({placeholders}) AND is_active = 1
                """, active_urls)

        affected = cursor.rowcount
        self.conn.commit()
        return affected

    def get_active_jobs(self, company: str = None) -> List[Dict]:
        """Get all active jobs, optionally filtered by company.

        Args:
            company: Optional company name to filter by

        Returns:
            List of job dictionaries
        """
        cursor = self.conn.cursor()

        if company:
            cursor.execute("""
                SELECT url, company, title, location, job_id,
                       first_seen, last_seen, scrape_count
                FROM jobs
                WHERE is_active = 1 AND company = ?
                ORDER BY company, title
            """, (company,))
        else:
            cursor.execute("""
                SELECT url, company, title, location, job_id,
                       first_seen, last_seen, scrape_count
                FROM jobs
                WHERE is_active = 1
                ORDER BY company, title
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_all_jobs(self, include_inactive: bool = False) -> List[Dict]:
        """Get all jobs from the database.

        Args:
            include_inactive: Whether to include inactive jobs

        Returns:
            List of job dictionaries
        """
        cursor = self.conn.cursor()

        if include_inactive:
            cursor.execute("""
                SELECT url, company, title, location, job_id,
                       first_seen, last_seen, scrape_count, is_active
                FROM jobs
                ORDER BY company, title
            """)
        else:
            cursor.execute("""
                SELECT url, company, title, location, job_id,
                       first_seen, last_seen, scrape_count
                FROM jobs
                WHERE is_active = 1
                ORDER BY company, title
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent scrape runs with statistics.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of scrape run dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, started_at, completed_at, sites_scraped,
                   jobs_found, jobs_new, jobs_updated, jobs_deactivated,
                   status, error_message
            FROM scrape_runs
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Get overall database statistics.

        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()

        # Total jobs
        cursor.execute("SELECT COUNT(*) as total FROM jobs")
        total_jobs = cursor.fetchone()['total']

        # Active jobs
        cursor.execute("SELECT COUNT(*) as active FROM jobs WHERE is_active = 1")
        active_jobs = cursor.fetchone()['active']

        # Inactive jobs
        inactive_jobs = total_jobs - active_jobs

        # Jobs by company
        cursor.execute("""
            SELECT company, COUNT(*) as count
            FROM jobs
            WHERE is_active = 1
            GROUP BY company
            ORDER BY count DESC
        """)
        jobs_by_company = {row['company']: row['count'] for row in cursor.fetchall()}

        # Total scrape runs
        cursor.execute("SELECT COUNT(*) as runs FROM scrape_runs")
        total_runs = cursor.fetchone()['runs']

        # Last scrape run
        cursor.execute("""
            SELECT started_at, jobs_new, jobs_updated, jobs_deactivated
            FROM scrape_runs
            WHERE status = 'completed'
            ORDER BY started_at DESC
            LIMIT 1
        """)
        last_run = cursor.fetchone()

        return {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'inactive_jobs': inactive_jobs,
            'jobs_by_company': jobs_by_company,
            'total_scrape_runs': total_runs,
            'last_run': dict(last_run) if last_run else None
        }

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test the database
    print("Testing JobDatabase...")

    # Create test database
    db = JobDatabase("data/test_jobs.db")

    # Start a scrape run
    run_id = db.start_scrape_run()
    print(f"✓ Started scrape run: {run_id}")

    # Add some test jobs
    test_jobs = [
        {
            'url': 'https://example.com/job1',
            'company': 'Test Company',
            'title': 'Software Engineer',
            'location': 'New York, NY',
            'job_id': 'JOB001'
        },
        {
            'url': 'https://example.com/job2',
            'company': 'Test Company',
            'title': 'Senior Engineer',
            'location': 'San Francisco, CA',
            'job_id': 'JOB002'
        }
    ]

    stats = {'new': 0, 'updated': 0, 'unchanged': 0}
    for job in test_jobs:
        action, changed = db.upsert_job(job)
        stats[action] += 1

    print(f"✓ Added {stats['new']} new jobs")

    # Update existing job
    test_jobs[0]['title'] = 'Senior Software Engineer'
    action, changed = db.upsert_job(test_jobs[0])
    print(f"✓ Updated job: {action}, changed={changed}")

    # Complete scrape run
    db.complete_scrape_run(run_id, {
        'sites_scraped': 1,
        'jobs_found': 2,
        'jobs_new': stats['new'],
        'jobs_updated': 1,
        'jobs_deactivated': 0,
        'status': 'completed'
    })
    print(f"✓ Completed scrape run")

    # Get statistics
    db_stats = db.get_stats()
    print(f"\n✓ Database Statistics:")
    print(f"  Total jobs: {db_stats['total_jobs']}")
    print(f"  Active jobs: {db_stats['active_jobs']}")
    print(f"  Inactive jobs: {db_stats['inactive_jobs']}")
    print(f"  Total runs: {db_stats['total_scrape_runs']}")

    # Get recent runs
    runs = db.get_recent_runs(limit=5)
    print(f"\n✓ Recent Scrape Runs:")
    for run in runs:
        print(f"  Run {run['id']}: {run['jobs_new']} new, {run['jobs_updated']} updated")

    db.close()
    print("\n✅ Database tests passed!")
