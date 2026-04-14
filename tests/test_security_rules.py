# @file test_security_rules.py
# @author Zavier
# @date 2026-04-14
"""
Parses security.md and asserts that all four required sections are present.

The security rules mandate: (1) explicit Permission before adding MCP servers
or APIs, (2) Caching for complex site code, (3) Rate Limiting on every entry
point, and (4) a Security Review on every code change. These tests confirm
none of those sections have been accidentally removed or renamed.
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SECURITY_RULES_PATH = REPO_ROOT / ".claude" / "rules" / "security.md"

# Keywords that uniquely identify each required section heading.
REQUIRED_SECTION_KEYWORDS = {
    "permission": "Permission",
    "caching": "Caching",
    "rate_limiting": "Rate Limiting",
    "security_review": "Security Review",
}


class TestSecurityRules(unittest.TestCase):
    """Asserts every mandatory section exists in security.md."""

    @classmethod
    def setUpClass(cls):
        """Read security.md once and share the content across all test methods."""
        cls.security_content = SECURITY_RULES_PATH.read_text(encoding="utf-8")

    def test_permission_section_should_be_present_when_security_md_is_valid(self):
        """Confirm the Permission section exists in security.md."""
        self.assertIn(
            REQUIRED_SECTION_KEYWORDS["permission"],
            self.security_content,
            "security.md is missing the 'Permission' section",
        )

    def test_caching_section_should_be_present_when_security_md_is_valid(self):
        """Confirm the Caching section exists in security.md."""
        self.assertIn(
            REQUIRED_SECTION_KEYWORDS["caching"],
            self.security_content,
            "security.md is missing the 'Caching' section",
        )

    def test_rate_limiting_section_should_be_present_when_security_md_is_valid(self):
        """Confirm the Rate Limiting section exists in security.md."""
        self.assertIn(
            REQUIRED_SECTION_KEYWORDS["rate_limiting"],
            self.security_content,
            "security.md is missing the 'Rate Limiting' section",
        )

    def test_security_review_section_should_be_present_when_security_md_is_valid(self):
        """Confirm the Security Review section exists in security.md."""
        self.assertIn(
            REQUIRED_SECTION_KEYWORDS["security_review"],
            self.security_content,
            "security.md is missing the 'Security Review' section",
        )

    def test_all_required_sections_should_be_present_when_security_md_is_complete(self):
        """Confirm no required keyword is absent from security.md."""
        missing_sections = [
            label
            for label, keyword in REQUIRED_SECTION_KEYWORDS.items()
            if keyword not in self.security_content
        ]
        self.assertEqual(
            missing_sections,
            [],
            f"security.md is missing sections: {missing_sections}",
        )


if __name__ == "__main__":
    unittest.main()
