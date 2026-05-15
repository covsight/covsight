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


def test_testplan_help():
    result = subprocess.run(["covsight", "testplan", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    for sub in ("show", "validate", "stats", "convert", "import", "export", "closure", "export-junit"):
        assert sub in result.stdout, f"testplan subcommand '{sub}' missing from --help"
