import os
import subprocess
import sys

import pytest

EXAMPLE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../examples/simple_example.ymr"))

EXPECTED_OUTPUT_LINES = [
    "Hello, Ymir!",
    "10 + 20 = 30",
    "Check positive: Non-positive",
    "3",
    "2",
    "1",
    "Liftoff!",
]


@pytest.mark.integration
def test_example_script_runs_and_outputs_expected_lines():
    result = subprocess.run(
        [sys.executable, "-m", "ymir.cli.ymir_cli", "run", EXAMPLE_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=20,
    )
    output = result.stdout + result.stderr
    # Check that all expected lines are in the output
    for line in EXPECTED_OUTPUT_LINES:
        assert line in output, f"Expected line not found in output: {line}\nFull output:\n{output}"
    # Check that the process exited successfully
    assert result.returncode == 0, f"Expected successful exit, got return code {result.returncode}"
