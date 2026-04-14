# @file test_agents_present.py
# @author Zavier
# @date 2026-04-14
"""
Verifies that every required subagent specification file exists inside
.claude/agents/subagents/ and is non-empty.

The agent pipeline requires four markdown specs — agent-coordinator,
code-architect, code-engineer, and code-reviewer — to be present before
any task begins. These tests confirm the specs are on disk and contain
content so the pipeline cannot run on missing or blank definitions.
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents" / "subagents"

EXPECTED_AGENTS = [
    "agent-coordinator.md",
    "code-architect.md",
    "code-engineer.md",
    "code-reviewer.md",
]


class TestAgentsPresent(unittest.TestCase):
    """Asserts every subagent spec file exists and is non-empty."""

    def test_agent_coordinator_md_should_exist_when_subagents_dir_is_present(self):
        """Confirm agent-coordinator.md is on disk."""
        agent_path = AGENTS_DIR / "agent-coordinator.md"
        self.assertTrue(
            agent_path.exists(),
            f"Expected agent spec not found: {agent_path}",
        )

    def test_agent_coordinator_md_should_be_non_empty_when_file_exists(self):
        """Confirm agent-coordinator.md contains at least one byte."""
        agent_path = AGENTS_DIR / "agent-coordinator.md"
        self.assertGreater(
            agent_path.stat().st_size,
            0,
            f"Agent spec is empty: {agent_path}",
        )

    def test_code_architect_md_should_exist_when_subagents_dir_is_present(self):
        """Confirm code-architect.md is on disk."""
        agent_path = AGENTS_DIR / "code-architect.md"
        self.assertTrue(
            agent_path.exists(),
            f"Expected agent spec not found: {agent_path}",
        )

    def test_code_architect_md_should_be_non_empty_when_file_exists(self):
        """Confirm code-architect.md contains at least one byte."""
        agent_path = AGENTS_DIR / "code-architect.md"
        self.assertGreater(
            agent_path.stat().st_size,
            0,
            f"Agent spec is empty: {agent_path}",
        )

    def test_code_engineer_md_should_exist_when_subagents_dir_is_present(self):
        """Confirm code-engineer.md is on disk."""
        agent_path = AGENTS_DIR / "code-engineer.md"
        self.assertTrue(
            agent_path.exists(),
            f"Expected agent spec not found: {agent_path}",
        )

    def test_code_engineer_md_should_be_non_empty_when_file_exists(self):
        """Confirm code-engineer.md contains at least one byte."""
        agent_path = AGENTS_DIR / "code-engineer.md"
        self.assertGreater(
            agent_path.stat().st_size,
            0,
            f"Agent spec is empty: {agent_path}",
        )

    def test_code_reviewer_md_should_exist_when_subagents_dir_is_present(self):
        """Confirm code-reviewer.md is on disk."""
        agent_path = AGENTS_DIR / "code-reviewer.md"
        self.assertTrue(
            agent_path.exists(),
            f"Expected agent spec not found: {agent_path}",
        )

    def test_code_reviewer_md_should_be_non_empty_when_file_exists(self):
        """Confirm code-reviewer.md contains at least one byte."""
        agent_path = AGENTS_DIR / "code-reviewer.md"
        self.assertGreater(
            agent_path.stat().st_size,
            0,
            f"Agent spec is empty: {agent_path}",
        )

    def test_all_expected_agents_should_be_present_when_subagents_dir_is_configured(self):
        """Confirm every entry in EXPECTED_AGENTS resolves to an existing file."""
        missing = [
            name for name in EXPECTED_AGENTS
            if not (AGENTS_DIR / name).exists()
        ]
        self.assertEqual(
            missing,
            [],
            f"Missing agent spec files: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
