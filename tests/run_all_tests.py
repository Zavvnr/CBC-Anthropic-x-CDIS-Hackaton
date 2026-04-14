# @file run_all_tests.py
# @author Zavier
# @date 2026-04-14
"""
Orchestrator that discovers, runs, and summarises all test modules in this
directory, then exits with code 0 if every test passes or code 1 if any fail.

Run from the repo root:
    python tests/run_all_tests.py

Each test module is loaded individually so failures in one file never
prevent the remaining modules from executing. A per-module PASS/FAIL line
is printed after all suites complete, followed by an overall result.
"""

import importlib
import io
import pathlib
import sys
import unittest

# Ensure the repo root is on sys.path so `tests.*` modules are importable
# regardless of the working directory the script is launched from.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


TEST_MODULE_NAMES = [
    "tests.test_rules_present",
    "tests.test_agents_present",
    "tests.test_validate_script",
    "tests.test_workflow_compliance",
    "tests.test_security_rules",
]


def load_suite_from_module(module_name):
    """Import a test module by dotted name and return its full TestSuite."""
    module = importlib.import_module(module_name)
    loader = unittest.TestLoader()
    return loader.loadTestsFromModule(module)


def run_suite(suite):
    """Run a TestSuite in a string buffer and return the TestResult."""
    buffer = io.StringIO()
    runner = unittest.TextTestRunner(stream=buffer, verbosity=2)
    result = runner.run(suite)
    return result, buffer.getvalue()


def print_module_summary(module_name, result, captured_output):
    """Print the verbose test output followed by a single PASS/FAIL line."""
    print(captured_output, end="")
    is_passing = result.wasSuccessful()
    status_label = "PASS" if is_passing else "FAIL"
    print(f"[{status_label}] {module_name}")
    print()


def main():
    """Run every test module and exit 0 on full success, 1 on any failure."""
    has_any_failure = False

    print("=" * 60)
    print("Running all test modules")
    print("=" * 60)
    print()

    for module_name in TEST_MODULE_NAMES:
        try:
            suite = load_suite_from_module(module_name)
            result, captured_output = run_suite(suite)
            print_module_summary(module_name, result, captured_output)

            if not result.wasSuccessful():
                has_any_failure = True

        except Exception as load_error:
            print(f"[ERROR] Could not load {module_name}: {load_error}")
            has_any_failure = True
            print()

    print("=" * 60)
    overall_label = "ALL TESTS PASSED" if not has_any_failure else "SOME TESTS FAILED"
    print(f"Result: {overall_label}")
    print("=" * 60)

    sys.exit(1 if has_any_failure else 0)


if __name__ == "__main__":
    main()
