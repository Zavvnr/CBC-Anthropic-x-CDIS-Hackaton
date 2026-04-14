# @file test_rules_present.py
# @author Zavier
# @date 2026-04-14
"""
Verifies that every required rule file exists inside .claude/rules/ and is non-empty.

The .claude/rules/ directory must contain four Markdown files that govern
code style, security, testing, and general preferences. These tests confirm
the files are present on disk and contain at least one byte of content so that
downstream agents are never working from an empty or missing ruleset.
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / ".claude" / "rules"

EXPECTED_RULES = [
    "code-style.md",
    "security.md",
    "testing.md",
    "preferences.md",
]


class TestRulesPresent(unittest.TestCase):
    """Asserts every rule file exists and is non-empty."""

    def test_code_style_md_should_exist_when_rules_directory_is_present(self):
        """Confirm code-style.md is on disk."""
        rule_path = RULES_DIR / "code-style.md"
        self.assertTrue(
            rule_path.exists(),
            f"Expected rule file not found: {rule_path}",
        )

    def test_code_style_md_should_be_non_empty_when_file_exists(self):
        """Confirm code-style.md contains at least one byte."""
        rule_path = RULES_DIR / "code-style.md"
        self.assertGreater(
            rule_path.stat().st_size,
            0,
            f"Rule file is empty: {rule_path}",
        )

    def test_security_md_should_exist_when_rules_directory_is_present(self):
        """Confirm security.md is on disk."""
        rule_path = RULES_DIR / "security.md"
        self.assertTrue(
            rule_path.exists(),
            f"Expected rule file not found: {rule_path}",
        )

    def test_security_md_should_be_non_empty_when_file_exists(self):
        """Confirm security.md contains at least one byte."""
        rule_path = RULES_DIR / "security.md"
        self.assertGreater(
            rule_path.stat().st_size,
            0,
            f"Rule file is empty: {rule_path}",
        )

    def test_testing_md_should_exist_when_rules_directory_is_present(self):
        """Confirm testing.md is on disk."""
        rule_path = RULES_DIR / "testing.md"
        self.assertTrue(
            rule_path.exists(),
            f"Expected rule file not found: {rule_path}",
        )

    def test_testing_md_should_be_non_empty_when_file_exists(self):
        """Confirm testing.md contains at least one byte."""
        rule_path = RULES_DIR / "testing.md"
        self.assertGreater(
            rule_path.stat().st_size,
            0,
            f"Rule file is empty: {rule_path}",
        )

    def test_preferences_md_should_exist_when_rules_directory_is_present(self):
        """Confirm preferences.md is on disk."""
        rule_path = RULES_DIR / "preferences.md"
        self.assertTrue(
            rule_path.exists(),
            f"Expected rule file not found: {rule_path}",
        )

    def test_preferences_md_should_be_non_empty_when_file_exists(self):
        """Confirm preferences.md contains at least one byte."""
        rule_path = RULES_DIR / "preferences.md"
        self.assertGreater(
            rule_path.stat().st_size,
            0,
            f"Rule file is empty: {rule_path}",
        )

    def test_all_expected_rules_should_be_present_when_rules_dir_is_configured(self):
        """Confirm every entry in EXPECTED_RULES resolves to an existing file."""
        missing = [
            name for name in EXPECTED_RULES
            if not (RULES_DIR / name).exists()
        ]
        self.assertEqual(
            missing,
            [],
            f"Missing rule files: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
