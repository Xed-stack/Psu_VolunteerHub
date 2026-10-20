"""Run the shared JavaScript behavioral regression with Node's built-in runner."""
from pathlib import Path
import shutil
import subprocess

import pytest


def test_form_submit_state_behavior():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is required for the JavaScript regression checks')
    result = subprocess.run(
        [node, '--test', str(Path(__file__).with_name('form-submit-state.test.cjs'))],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
