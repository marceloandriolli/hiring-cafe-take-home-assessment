# Test Suite - Avature ATS Scraper

Comprehensive test coverage for all 4 phases of the Avature ATS Scraper system.

## Overview

This test suite validates all components across the 4-phase evolution of the scraper:

- **Phase 1:** Basic scraping functionality
- **Phase 2:** Database and incremental updates
- **Phase 3:** Async scraping with connection pooling
- **Phase 4:** Fuzzy deduplication with normalization

## Quick Start

### Run All Tests

```bash
# From project root
python tests/run_all_tests.py

# Or from tests directory
cd tests
python run_all_tests.py
```

### Run Individual Phases

```bash
# Phase 1: Basic Scraper
python tests/run_all_tests.py --phase 1

# Phase 2: Database & Incremental
python tests/run_all_tests.py --phase 2

# Phase 3: Async Scraping
python tests/run_all_tests.py --phase 3

# Phase 4: Deduplication
python tests/run_all_tests.py --phase 4
```

### Run Individual Test Files

```bash
# Run specific test file
python tests/test_phase1_scraper.py
python tests/test_phase2_database.py
python tests/test_phase3_async.py
python tests/test_phase4_deduplication.py
```

## Test Files

### `test_phase1_scraper.py` (Phase 1: Basic Scraper)

Tests core scraping functionality:

- **Scraper Initialization** (3 tests)
  - Scraper creation
  - Default settings
  - Configuration validation

- **Job Extraction** (4 tests)
  - HTML parsing finds jobs
  - Title extraction
  - URL extraction
  - Location extraction

- **URL Construction** (4 tests)
  - Base URL format
  - Search URL construction
  - Pagination URLs
  - Job detail URLs

- **Job Data Structure** (4 tests)
  - Required fields validation
  - Title not empty
  - URL format validation
  - Company extraction

- **Error Handling** (3 tests)
  - Empty HTML handling
  - Malformed HTML resilience
  - Missing fields handling

- **Pagination Logic** (2 tests)
  - URL format validation
  - Page range generation

- **Data Validation** (3 tests)
  - Whitespace trimming
  - URL normalization
  - Job ID extraction

- **Company Extraction** (3 tests)
  - Bloomberg URL
  - Meta URL
  - UCLA Health URL

- **Rate Limiting** (1 test)
  - Sleep delays configuration

**Total: ~27 tests**

### `test_phase2_database.py` (Phase 2: Database & Incremental)

Tests database layer and incremental scraping:

- **Database Initialization** (3 tests)
  - Database file creation
  - Table schema validation
  - Index creation

- **Job Upsert** (4 tests)
  - Insert new job
  - Update existing job with changes
  - Unchanged job detection
  - Scrape count increment

- **Job Lifecycle** (3 tests)
  - first_seen timestamp
  - last_seen updates
  - Active status initialization

- **Job Deactivation** (2 tests)
  - Mark missing jobs inactive
  - Reactivate jobs

- **Statistics** (3 tests)
  - Get database stats
  - Filter by company
  - Get all active jobs

- **Smart Stopping** (2 tests)
  - Threshold validation
  - Counter reset logic

- **Database Queries** (2 tests)
  - Query by URL
  - Filter active jobs only

**Total: ~19 tests**

### `test_phase3_async.py` (Phase 3: Async Scraping)

Tests async scraping with aiohttp:

- **Scraper Initialization** (3 tests)
  - Async scraper creation
  - Configuration parameters
  - Semaphore initialization

- **Connection Pooling** (2 tests)
  - TCP connector limits
  - Session with connector

- **Semaphore Control** (3 tests)
  - Concurrent operation limiting
  - Site semaphore limits
  - Page semaphore limits

- **Concurrent Operations** (3 tests)
  - Gather multiple tasks
  - Concurrent sites scraping
  - Concurrent pages scraping

- **Error Isolation** (2 tests)
  - Gather with return_exceptions
  - Single failure doesn't block others

- **Performance** (2 tests)
  - Async faster than sync
  - Connection pooling reuse

- **Session Management** (2 tests)
  - Session creation
  - Session cleanup

- **Async Patterns** (2 tests)
  - Context manager usage
  - Gather order preservation

- **Concurrency Limits** (3 tests)
  - Default limits
  - Custom limits
  - Conservative limits

- **Integration** (1 test)
  - Async results to database

**Total: ~23 tests**

### `test_phase4_deduplication.py` (Phase 4: Fuzzy Deduplication)

Tests normalization and duplicate detection:

- **Text Normalization** (5 tests)
  - Basic title normalization
  - Senior abbreviation expansion
  - Junior abbreviation expansion
  - Software engineer abbreviations
  - Tech abbreviations (QA, ML, AI)

- **Location Normalization** (5 tests)
  - Basic location normalization
  - NYC abbreviation expansion
  - SF abbreviation expansion
  - LA abbreviation expansion
  - State abbreviations

- **Similarity Algorithms** (6 tests)
  - Sequence similarity (identical, different, similar)
  - Jaccard similarity (identical, different, overlap)

- **Duplicate Detection** (4 tests)
  - Identical jobs are duplicates
  - Abbreviated vs full forms
  - Different companies not duplicates
  - Different titles not duplicates

- **Similarity Thresholds** (3 tests)
  - Title threshold (85%)
  - Location threshold (90%)
  - Combined threshold (80%)

- **Company-Scoped Deduplication** (1 test)
  - Only compare within company

- **Duplicate Grouping** (2 tests)
  - Group duplicates logic
  - Keep canonical job

- **Deduplication Report** (2 tests)
  - Report structure
  - Group structure with scores

- **Edge Cases** (4 tests)
  - Empty title handling
  - None location handling
  - Special characters
  - Multiple spaces

- **Performance** (2 tests)
  - Normalization speed
  - Company scoping reduces comparisons

**Total: ~34 tests**

## Test Statistics

| Phase | Test File | Tests | Focus Area |
|-------|-----------|-------|------------|
| **Phase 1** | `test_phase1_scraper.py` | ~27 | HTML parsing, extraction, validation |
| **Phase 2** | `test_phase2_database.py` | ~19 | SQLite, upsert, lifecycle, smart stopping |
| **Phase 3** | `test_phase3_async.py` | ~23 | aiohttp, semaphores, concurrency, performance |
| **Phase 4** | `test_phase4_deduplication.py` | ~34 | Normalization, similarity, deduplication |
| **Total** | **4 files** | **~103 tests** | **Complete system coverage** |

## Test Coverage

### Phase 1 Coverage
- ✅ Scraper initialization and configuration
- ✅ HTML parsing with BeautifulSoup
- ✅ Job extraction (title, URL, ID, location)
- ✅ URL construction and validation
- ✅ Pagination logic
- ✅ Error handling (empty HTML, malformed HTML)
- ✅ Data validation and cleaning
- ✅ Company name extraction
- ✅ Rate limiting configuration

### Phase 2 Coverage
- ✅ Database creation and schema
- ✅ Upsert logic (new/updated/unchanged)
- ✅ Job lifecycle tracking
- ✅ Scrape count incrementing
- ✅ Job deactivation and reactivation
- ✅ Smart stopping algorithm
- ✅ Statistics and reporting
- ✅ Database queries and filtering

### Phase 3 Coverage
- ✅ Async scraper initialization
- ✅ aiohttp session management
- ✅ Connection pooling (TCPConnector)
- ✅ Semaphore rate limiting
- ✅ Concurrent operations (sites and pages)
- ✅ Error isolation (gather with exceptions)
- ✅ Performance improvements validation
- ✅ Async patterns and best practices

### Phase 4 Coverage
- ✅ Text normalization (30+ rules)
- ✅ Title abbreviation expansion
- ✅ Location normalization
- ✅ Sequence similarity algorithm
- ✅ Jaccard similarity algorithm
- ✅ Duplicate detection logic
- ✅ Similarity thresholds (85%/90%/80%)
- ✅ Company-scoped deduplication
- ✅ Duplicate grouping and reporting
- ✅ Edge cases and special characters

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt

# Ensure all source files are in place
ls src/*.py
```

### Command Line Options

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific phase
python tests/run_all_tests.py --phase 1
python tests/run_all_tests.py --phase 2
python tests/run_all_tests.py --phase 3
python tests/run_all_tests.py --phase 4

# Verbose output
python tests/run_all_tests.py -v

# List available phases
python tests/run_all_tests.py --list
```

### Expected Output

```
================================================================================
                 AVATURE ATS SCRAPER - COMPLETE TEST SUITE
                            Version 1.4.0
                    Test Run: 2026-02-04 10:30:00
================================================================================

================================================================================
                          PHASE 1: Basic Scraper
================================================================================
test_scraper_creation (test_phase1_scraper.TestAvatureScraperInitialization) ... ok
test_parse_html_finds_jobs (test_phase1_scraper.TestJobExtraction) ... ok
...
----------------------------------------------------------------------
Ran 27 tests in 0.145s

OK

================================================================================
                 PHASE 2: Database & Incremental Updates
================================================================================
...

================================================================================
                         TEST SUMMARY - ALL PHASES
================================================================================

Phase 1                        ✅ PASS      27 tests   27 passed   0 failed   0 errors  (100.0%)
Phase 2                        ✅ PASS      19 tests   19 passed   0 failed   0 errors  (100.0%)
Phase 3                        ✅ PASS      23 tests   23 passed   0 failed   0 errors  (100.0%)
Phase 4                        ✅ PASS      34 tests   34 passed   0 failed   0 errors  (100.0%)

--------------------------------------------------------------------------------
TOTAL                                      103 tests  103 passed   0 failed   0 errors  (100.0%)
================================================================================

                        🎉 ALL TESTS PASSED! 🎉
              The system is ready for production deployment.

================================================================================
```

## Test Architecture

### Unit Tests
- Isolated component testing
- Mock external dependencies
- Fast execution (<1s per phase)

### Integration Tests
- Database operations with temp files
- Async operations with real event loops
- End-to-end workflows

### Test Fixtures
- Temporary databases for Phase 2
- Mock async scrapers for Phase 3
- Sample job data for all phases

## Continuous Testing

### Pre-Commit
```bash
# Run tests before committing
python tests/run_all_tests.py
git commit -m "Your message"
```

### CI/CD Integration
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python tests/run_all_tests.py
```

## Troubleshooting

### ImportError: No module named 'src'
```bash
# Run from project root, not tests directory
cd /path/to/avature_ats_scraper
python tests/run_all_tests.py
```

### Database Locked Error
```bash
# Close any open SQLite connections
# Delete temp test databases
rm -f /tmp/test_*.db
```

### Async Test Failures
```bash
# Ensure aiohttp is installed
pip install aiohttp

# Check Python version (requires 3.9+)
python --version
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Add tests to appropriate phase file
3. Update test count in this README
4. Ensure all tests pass before committing

### Test Naming Convention
```python
def test_<component>_<behavior>(self):
    """Test that <expected behavior>"""
```

### Test Structure
```python
class Test<Component>(unittest.TestCase):
    """Test <component> functionality"""

    def setUp(self):
        """Set up test fixtures"""
        pass

    def tearDown(self):
        """Clean up after tests"""
        pass

    def test_something(self):
        """Test description"""
        # Arrange
        # Act
        # Assert
```

## Performance Benchmarks

Expected test execution times:

| Phase | Tests | Time | Throughput |
|-------|-------|------|------------|
| Phase 1 | 27 | <0.2s | >135 tests/sec |
| Phase 2 | 19 | <0.5s | >38 tests/sec |
| Phase 3 | 23 | <1.0s | >23 tests/sec |
| Phase 4 | 34 | <0.5s | >68 tests/sec |
| **Total** | **103** | **<2.5s** | **>41 tests/sec** |

## Documentation

- **Architecture:** See `COMPLETE_ARCHITECTURE.md` for system design
- **Strategy:** See `STRATEGY.md` for implementation approach
- **Usage:** See `README.md` for usage examples

## Support

For issues or questions:
- Check test output for detailed failure messages
- Review COMPLETE_ARCHITECTURE.md for component details
- Run individual test files for focused debugging

---

**Version:** 1.4.0
**Last Updated:** 2026-02-04
**Test Coverage:** All 4 phases, 103 tests
