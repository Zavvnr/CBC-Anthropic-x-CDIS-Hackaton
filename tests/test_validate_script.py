# @file test_validate_script.py
# @author Zavier
# @date 2026-04-14
"""
Verifies that the validate.sh script exists, is executable, and runs
successfully against a minimal well-formed Python sample file.

validate.sh enforces code-formatting rules (file header, no magic numbers,
function docstrings, indentation, and line length). These tests confirm the
script is present, reachable by bash, and returns exit code 0 when given
a file that meets all its requirements.
"""

import os
import pathlib
import platform
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
VALIDATE_SCRIPT_PATH = (
    REPO_ROOT / ".claude" / "my-plugin" / "skills" / "scripts" / "validate.sh"
)

# A minimal Python file that satisfies every validate.sh check:
#   - @file header in first 5 lines
#   - no large numeric literals
#   - every def has a docstring on the very next line
#   - 4-space indentation (no tabs)
#   - all lines under 120 characters
SAMPLE_PYTHON_CONTENT = '''\
# @file sample_valid.py
# @author test
# @date 2026-04-14

def greet(name):
    """Return a greeting string for the given name."""
    return "Hello, " + name
'''

IS_WINDOWS = platform.system() == "Windows"


class TestValidateScript(unittest.TestCase):
    """Asserts validate.sh exists, is executable, and passes on a valid file."""

    def test_validate_script_should_exist_when_my_plugin_is_configured(self):
        """Confirm validate.sh is present at the expected path."""
        self.assertTrue(
            VALIDATE_SCRIPT_PATH.exists(),
            f"validate.sh not found at: {VALIDATE_SCRIPT_PATH}",
        )

    @unittest.skipIf(IS_WINDOWS, "Executable bit check is not applicable on Windows")
    def test_validate_script_should_be_executable_when_script_exists(self):
        """Confirm the OS executable bit is set on validate.sh."""
        is_executable = os.access(str(VALIDATE_SCRIPT_PATH), os.X_OK)
        self.assertTrue(
            is_executable,
            f"validate.sh is not executable: {VALIDATE_SCRIPT_PATH}",
        )

    @unittest.skipIf(
        IS_WINDOWS and shutil.which("bash") is None,
        "bash is not available on this Windows environment — skipping execution test",
    )
    def test_validate_script_should_run_without_error_when_given_sample_python_file(self):
        """Run validate.sh against a minimal valid .py file and expect exit code 0."""
        temp_dir = tempfile.mkdtemp()
        sample_file = os.path.join(temp_dir, "sample_valid.py")

        try:
            with open(sample_file, "w", encoding="utf-8") as file_handle:
                file_handle.write(SAMPLE_PYTHON_CONTENT)

            bash_executable = shutil.which("bash") or "bash"
            result = subprocess.run(
                [bash_executable, str(VALIDATE_SCRIPT_PATH), sample_file],
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                (
                    f"validate.sh exited with {result.returncode}.\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                ),
            )
        finally:
            # Always clean up the temp directory regardless of test outcome.
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
