"""Smoke tests for the atlas CLI."""

import subprocess
import sys


def test_atlas_import():
    """Test that the atlas package can be imported."""
    import tools.atlas

    assert hasattr(tools.atlas, "__version__")


def test_atlas_help():
    """Test that atlas --help works."""
    result = subprocess.run([sys.executable, "-m", "tools.atlas", "--help"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert "atlas" in result.stdout.lower()
    assert "validate" in result.stdout
    assert "crawl" in result.stdout
    assert "build" in result.stdout
    assert "stats" in result.stdout


def test_atlas_version():
    """Test that atlas --version works."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.atlas", "--version"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert "atlas" in result.stdout.lower()


def test_validate_command():
    """Test that atlas validate runs without error."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.atlas", "validate"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert "validating" in result.stdout.lower() or "valid" in result.stdout.lower()


def test_crawl_command():
    """Test that atlas crawl runs without error."""
    result = subprocess.run([sys.executable, "-m", "tools.atlas", "crawl"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0


def test_build_command():
    """Test that atlas build runs without error."""
    result = subprocess.run([sys.executable, "-m", "tools.atlas", "build"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0


def test_stats_command():
    """Test that atlas stats runs without error."""
    result = subprocess.run([sys.executable, "-m", "tools.atlas", "stats"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0


def test_validate_wording_graceful_skip():
    """Test that validate --wording gracefully skips if wording_lint.py is missing."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.atlas", "validate", "--wording"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
