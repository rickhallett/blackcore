#!/usr/bin/env python3
"""Script to run integration tests for the minimal module."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_integration_tests(verbose=False, specific_test=None, show_coverage=False):
    """Run integration tests with various options."""
    # Get the integration test directory
    test_dir = Path(__file__).parent / "integration"

    # Build pytest command
    cmd = ["pytest"]

    if verbose:
        cmd.append("-v")

    if show_coverage:
        cmd.extend(["--cov=blackcore.minimal", "--cov-report=term-missing"])

    if specific_test:
        cmd.append(specific_test)
    else:
        cmd.append(str(test_dir))

    # Add markers for integration tests
    cmd.extend(["-m", "not unit"])

    print(f"Running command: {' '.join(cmd)}")
    print("-" * 50)

    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent.parent)

    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run integration tests for minimal module")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Show coverage report")
    parser.add_argument("-t", "--test", help="Run specific test file or test")
    parser.add_argument("--workflow", action="store_true", help="Run only workflow tests")
    parser.add_argument("--compliance", action="store_true", help="Run only compliance tests")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")

    args = parser.parse_args()

    # Determine which test to run
    specific_test = args.test
    if args.workflow:
        specific_test = "tests/integration/test_full_workflow.py"
    elif args.compliance:
        specific_test = "tests/integration/test_notion_compliance.py"
    elif args.performance:
        specific_test = "tests/integration/test_performance.py"

    # Run tests
    exit_code = run_integration_tests(
        verbose=args.verbose, specific_test=specific_test, show_coverage=args.coverage
    )

    if exit_code == 0:
        print("\n✅ All integration tests passed!")
    else:
        print("\n❌ Some integration tests failed!")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
