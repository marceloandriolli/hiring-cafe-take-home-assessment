#!/usr/bin/env python3
"""
Master Test Runner for All Phases

Runs comprehensive test suites for all 4 phases of the Avature ATS Scraper:
- Phase 1: Basic Scraper (HTML parsing, pagination, extraction)
- Phase 2: Database & Incremental Updates (SQLite, smart stopping, lifecycle)
- Phase 3: Async Scraping (aiohttp, connection pooling, semaphores)
- Phase 4: Fuzzy Deduplication (normalization, similarity matching)

Usage:
    python tests/run_all_tests.py              # Run all tests
    python tests/run_all_tests.py --phase 1    # Run specific phase
    python tests/run_all_tests.py --verbose    # Verbose output
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import argparse
from datetime import datetime


def run_all_phases(verbose=False):
    """Run tests for all phases"""
    from test_phase1_scraper import run_phase1_tests
    from test_phase2_database import run_phase2_tests
    from test_phase3_async import run_phase3_tests
    from test_phase4_deduplication import run_phase4_tests

    print("\n" + "=" * 80)
    print(" " * 20 + "AVATURE ATS SCRAPER - COMPLETE TEST SUITE")
    print(" " * 30 + f"Version 1.4.0")
    print(" " * 25 + f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    results = {}

    # Phase 1
    print("\n" + "=" * 80)
    print("PHASE 1: Basic Scraper".center(80))
    print("=" * 80)
    results['phase1'] = run_phase1_tests()

    # Phase 2
    print("\n\n" + "=" * 80)
    print("PHASE 2: Database & Incremental Updates".center(80))
    print("=" * 80)
    results['phase2'] = run_phase2_tests()

    # Phase 3
    print("\n\n" + "=" * 80)
    print("PHASE 3: Async Scraping".center(80))
    print("=" * 80)
    results['phase3'] = run_phase3_tests()

    # Phase 4
    print("\n\n" + "=" * 80)
    print("PHASE 4: Fuzzy Deduplication".center(80))
    print("=" * 80)
    results['phase4'] = run_phase4_tests()

    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY - ALL PHASES".center(80))
    print("=" * 80)

    total_tests = sum(r.testsRun for r in results.values())
    total_failures = sum(len(r.failures) for r in results.values())
    total_errors = sum(len(r.errors) for r in results.values())
    total_success = total_tests - total_failures - total_errors
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

    print()
    for phase, result in results.items():
        phase_name = phase.upper().replace('PHASE', 'Phase ')
        tests_run = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        success = tests_run - failures - errors
        rate = (success / tests_run * 100) if tests_run > 0 else 0

        status = "✅ PASS" if result.wasSuccessful() else "❌ FAIL"

        print(f"{phase_name:30} {status:10} "
              f"{tests_run:3} tests  "
              f"{success:3} passed  "
              f"{failures:2} failed  "
              f"{errors:2} errors  "
              f"({rate:5.1f}%)")

    print()
    print("-" * 80)
    print(f"{'TOTAL':30} {'':10} "
          f"{total_tests:3} tests  "
          f"{total_success:3} passed  "
          f"{total_failures:2} failed  "
          f"{total_errors:2} errors  "
          f"({success_rate:5.1f}%)")
    print("=" * 80)

    if success_rate == 100.0:
        print("\n" + "🎉 ALL TESTS PASSED! 🎉".center(80))
        print("The system is ready for production deployment.\n")
    elif success_rate >= 90.0:
        print("\n" + "⚠️  MOSTLY PASSING - Some tests need attention".center(80) + "\n")
    else:
        print("\n" + "❌ MULTIPLE FAILURES - Review required".center(80) + "\n")

    print("=" * 80 + "\n")

    # Return overall success
    return all(r.wasSuccessful() for r in results.values())


def run_single_phase(phase_num, verbose=False):
    """Run tests for a single phase"""
    from test_phase1_scraper import run_phase1_tests
    from test_phase2_database import run_phase2_tests
    from test_phase3_async import run_phase3_tests
    from test_phase4_deduplication import run_phase4_tests

    phase_runners = {
        1: run_phase1_tests,
        2: run_phase2_tests,
        3: run_phase3_tests,
        4: run_phase4_tests
    }

    if phase_num not in phase_runners:
        print(f"Error: Invalid phase number {phase_num}. Must be 1-4.")
        return False

    print(f"\n{'=' * 80}")
    print(f"Running Phase {phase_num} Tests Only".center(80))
    print(f"{'=' * 80}\n")

    result = phase_runners[phase_num]()

    print(f"\n{'=' * 80}")
    print(f"Phase {phase_num} Results".center(80))
    print(f"{'=' * 80}")
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print(f"{'=' * 80}\n")

    return result.wasSuccessful()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run Avature ATS Scraper test suites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_all_tests.py                    # Run all phases
  python tests/run_all_tests.py --phase 1          # Run Phase 1 only
  python tests/run_all_tests.py --phase 2 -v       # Run Phase 2 with verbose output

Test Coverage:
  Phase 1: Basic scraping (HTML parsing, pagination, extraction)
  Phase 2: Database & incremental updates (SQLite, smart stopping)
  Phase 3: Async scraping (aiohttp, connection pooling, semaphores)
  Phase 4: Fuzzy deduplication (normalization, similarity matching)
        """
    )

    parser.add_argument(
        '--phase',
        type=int,
        choices=[1, 2, 3, 4],
        help='Run tests for specific phase only (1-4)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose test output'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List available test phases'
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Test Phases:")
        print("  Phase 1: Basic Scraper")
        print("  Phase 2: Database & Incremental Updates")
        print("  Phase 3: Async Scraping")
        print("  Phase 4: Fuzzy Deduplication")
        print()
        return 0

    # Run tests
    if args.phase:
        success = run_single_phase(args.phase, args.verbose)
    else:
        success = run_all_phases(args.verbose)

    # Exit with appropriate code
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
