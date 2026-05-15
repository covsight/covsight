"""Smoke tests: CLI parses and dispatches correctly."""
import subprocess
import sys


def test_version():
    result = subprocess.run([sys.executable, "-m", "covsight", "--version"], capture_output=True, text=True)
    assert result.returncode == 0


def test_help():
    result = subprocess.run([sys.executable, "-m", "covsight", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "convert" in result.stdout
    assert "merge" in result.stdout
    assert "show" in result.stdout
