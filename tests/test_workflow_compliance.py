# @file test_workflow_compliance.py
# @author Zavier
# @date 2026-04-14
"""
Parses workflows.md and asserts that the mandatory three-phase sequence
headings are present and appear in the correct order.

The master workflow requires Phase 1 (read rules), Phase 2 (deploy subagents),
and Phase 3 (apply plugins) to be defined in that sequence. These tests confirm
the document structure matches the declared contract so any accidental edit
that removes or reorders a phase is caught immediately.
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS_PATH = REPO_ROOT / ".claude" / "rules" / "workflows.md"


class TestWorkflowCompliance(unittest.TestCase):
    """Asserts the three-phase sequence headings exist and are ordered correctly."""

    @classmethod
    def setUpClass(cls):
        """Read workflows.md once and share the content across all test methods."""
        cls.workflows_content = WORKFLOWS_PATH.read_text(encoding="utf-8")

    def test_phase_1_heading_should_be_present_when_workflows_md_is_valid(self):
        """Confirm 'Phase 1' appears in workflows.md."""
        self.assertIn(
            "Phase 1",
            self.workflows_content,
            "workflows.md is missing the 'Phase 1' heading",
        )

    def test_phase_2_heading_should_be_present_when_workflows_md_is_valid(self):
        """Confirm 'Phase 2' appears in workflows.md."""
        self.assertIn(
            "Phase 2",
            self.workflows_content,
            "workflows.md is missing the 'Phase 2' heading",
        )

    def test_phase_3_heading_should_be_present_when_workflows_md_is_valid(self):
        """Confirm 'Phase 3' appears in workflows.md."""
        self.assertIn(
            "Phase 3",
            self.workflows_content,
            "workflows.md is missing the 'Phase 3' heading",
        )

    def test_phases_should_appear_in_order_when_workflows_md_is_valid(self):
        """Confirm Phase 1 < Phase 2 < Phase 3 by character position in the file."""
        position_phase_1 = self.workflows_content.index("Phase 1")
        position_phase_2 = self.workflows_content.index("Phase 2")
        position_phase_3 = self.workflows_content.index("Phase 3")

        self.assertLess(
            position_phase_1,
            position_phase_2,
            "Phase 1 must appear before Phase 2 in workflows.md",
        )
        self.assertLess(
            position_phase_2,
            position_phase_3,
            "Phase 2 must appear before Phase 3 in workflows.md",
        )


if __name__ == "__main__":
    unittest.main()
