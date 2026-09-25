#!/usr/bin/env python3
"""Tests for README stats automation (S4-1)."""

import json
import tempfile
from pathlib import Path

import pytest

from tools.atlas.stats import format_stats_block, update_readme_stats, validate_readme_stats


def test_format_stats_block_empty():
    """Test formatting with empty/seed stats."""
    stats = {
        "total_skills": 0,
        "canonical_skills": 0,
        "repositories": 0,
        "curated_skills": 0,
        "by_license_class": {"allow": 0, "conditional": 0, "deny": 0, "unknown": 0},
        "by_trust_tier": {"official": 0, "community": 0, "aggregator-copy": 0, "unreviewed": 0},
        "spec_strict_valid_pct": 0.0,
        "tier1_freshness_p50_hours": None,
    }

    result = format_stats_block(stats)

    # Should include early preview message
    assert "Early preview: the index is being seeded" in result
    assert "[0](index/skills.jsonl)" in result


def test_format_stats_block_with_data():
    """Test formatting with real data."""
    stats = {
        "total_skills": 1234,
        "canonical_skills": 1100,
        "repositories": 45,
        "curated_skills": 23,
        "by_license_class": {"allow": 800, "conditional": 50, "deny": 100, "unknown": 284},
        "by_trust_tier": {"official": 100, "community": 500, "aggregator-copy": 200, "unreviewed": 434},
        "spec_strict_valid_pct": 85.5,
        "tier1_freshness_p50_hours": 36.5,
        "generated_at": "2026-09-25T10:00:00Z",
    }

    result = format_stats_block(stats)

    # Check all required elements
    assert "1,234" in result  # Total skills with thousands separator
    assert "1,100" in result  # Canonical count
    assert "45" in result  # Repositories
    assert "23" in result  # Curated
    assert "77.0%" in result  # License resolved: (800+50+100)/1234 = 950/1234 ≈ 77.0%
    assert "1.5 days" in result  # Freshness: 36.5 hours = 1.5 days
    assert "2026-09-25" in result  # Last updated date

    # Check links
    assert "[1,234](index/skills.jsonl)" in result
    assert "[45](index/sources.json)" in result
    assert "[23](curated/)" in result


def test_format_stats_block_freshness_hours():
    """Test freshness formatting in hours when < 24."""
    stats = {
        "total_skills": 100,
        "canonical_skills": 100,
        "repositories": 10,
        "curated_skills": 5,
        "by_license_class": {"allow": 50, "conditional": 0, "deny": 0, "unknown": 50},
        "tier1_freshness_p50_hours": 6.5,
    }

    result = format_stats_block(stats)
    assert "6.5 hours" in result


def test_update_readme_stats():
    """Test updating README with stats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create README with markers
        readme_path = tmpdir / "README.md"
        readme_content = """# Test README

Some content before.

<!-- atlas:stats:start -->
Old content here
<!-- atlas:stats:end -->

Some content after.
"""
        readme_path.write_text(readme_content)

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats = {
            "total_skills": 500,
            "canonical_skills": 450,
            "repositories": 20,
            "curated_skills": 10,
            "by_license_class": {"allow": 300, "conditional": 50, "deny": 50, "unknown": 100},
            "generated_at": "2026-09-25T10:00:00Z",
        }
        stats_path.write_text(json.dumps(stats))

        # Update README
        updated = update_readme_stats(readme_path, stats_path)
        assert updated is True

        # Read updated README
        new_content = readme_path.read_text()

        # Check that markers are preserved
        assert "<!-- atlas:stats:start -->" in new_content
        assert "<!-- atlas:stats:end -->" in new_content

        # Check that stats are present
        assert "500" in new_content
        assert "[20](index/sources.json)" in new_content
        assert "[10](curated/)" in new_content

        # Check that old content is gone
        assert "Old content here" not in new_content

        # Check that surrounding content is preserved
        assert "Some content before" in new_content
        assert "Some content after" in new_content


def test_update_readme_stats_no_change():
    """Test that update returns False when no change needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats = {
            "total_skills": 500,
            "canonical_skills": 450,
            "repositories": 20,
            "curated_skills": 10,
            "by_license_class": {"allow": 300, "conditional": 50, "deny": 50, "unknown": 100},
            "generated_at": "2026-09-25T10:00:00Z",
        }
        stats_path.write_text(json.dumps(stats))

        # Generate expected block
        expected_block = format_stats_block(stats)

        # Create README with correct content
        readme_path = tmpdir / "README.md"
        readme_content = f"""# Test README

<!-- atlas:stats:start -->
{expected_block}
<!-- atlas:stats:end -->

Some content after.
"""
        readme_path.write_text(readme_content)

        # Update should return False (no change)
        updated = update_readme_stats(readme_path, stats_path)
        assert updated is False


def test_update_readme_stats_missing_markers():
    """Test that update raises error when markers are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create README without markers
        readme_path = tmpdir / "README.md"
        readme_path.write_text("# README\n\nNo markers here.")

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats_path.write_text('{"total_skills": 0}')

        # Should raise ValueError
        with pytest.raises(ValueError, match="must contain.*atlas:stats:start"):
            update_readme_stats(readme_path, stats_path)


def test_validate_readme_stats_valid():
    """Test validation when README matches stats.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats = {
            "total_skills": 500,
            "canonical_skills": 450,
            "repositories": 20,
            "curated_skills": 10,
            "by_license_class": {"allow": 300, "conditional": 50, "deny": 50, "unknown": 100},
            "generated_at": "2026-09-25T10:00:00Z",
        }
        stats_path.write_text(json.dumps(stats))

        # Generate expected block
        expected_block = format_stats_block(stats)

        # Create README with correct content
        readme_path = tmpdir / "README.md"
        readme_content = f"""# Test README

<!-- atlas:stats:start -->
{expected_block}
<!-- atlas:stats:end -->
"""
        readme_path.write_text(readme_content)

        # Validate
        is_valid, errors = validate_readme_stats(readme_path, stats_path)
        assert is_valid is True
        assert len(errors) == 0


def test_validate_readme_stats_invalid():
    """Test validation when README doesn't match stats.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats = {
            "total_skills": 500,
            "canonical_skills": 450,
            "repositories": 20,
            "curated_skills": 10,
            "by_license_class": {"allow": 300, "conditional": 50, "deny": 50, "unknown": 100},
            "generated_at": "2026-09-25T10:00:00Z",
        }
        stats_path.write_text(json.dumps(stats))

        # Create README with wrong content
        readme_path = tmpdir / "README.md"
        readme_content = """# Test README

<!-- atlas:stats:start -->
- **Total skills:** 999 (wrong!)
<!-- atlas:stats:end -->
"""
        readme_path.write_text(readme_content)

        # Validate
        is_valid, errors = validate_readme_stats(readme_path, stats_path)
        assert is_valid is False
        assert len(errors) > 0
        assert any("does not match" in e for e in errors)


def test_validate_readme_stats_missing_file():
    """Test validation when stats.json doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        readme_path = tmpdir / "README.md"
        readme_path.write_text("# README\n<!-- atlas:stats:start -->\n<!-- atlas:stats:end -->")

        stats_path = tmpdir / "stats.json"  # Doesn't exist

        is_valid, errors = validate_readme_stats(readme_path, stats_path)
        assert is_valid is False
        assert any("not found" in e for e in errors)


def test_round_trip_consistency():
    """Test that stats -> format -> update -> validate is consistent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats = {
            "total_skills": 1234,
            "canonical_skills": 1100,
            "repositories": 45,
            "curated_skills": 23,
            "by_license_class": {"allow": 800, "conditional": 50, "deny": 100, "unknown": 284},
            "tier1_freshness_p50_hours": 36.5,
            "generated_at": "2026-09-25T10:00:00Z",
        }
        stats_path.write_text(json.dumps(stats, indent=2))

        # Create README with markers
        readme_path = tmpdir / "README.md"
        readme_content = """# Test README

<!-- atlas:stats:start -->
Old placeholder content
<!-- atlas:stats:end -->
"""
        readme_path.write_text(readme_content)

        # Update README from stats
        updated = update_readme_stats(readme_path, stats_path)
        assert updated is True

        # Validate that it matches
        is_valid, errors = validate_readme_stats(readme_path, stats_path)
        assert is_valid is True, f"Validation errors: {errors}"

        # Update again (should be no-op)
        updated_again = update_readme_stats(readme_path, stats_path)
        assert updated_again is False

        # Should still be valid
        is_valid, errors = validate_readme_stats(readme_path, stats_path)
        assert is_valid is True


def test_no_manual_numbers_outside_block():
    """Test that validates numbers only come from generated block."""
    # This is more of a wording lint concern, but we ensure the function
    # only updates content within the markers
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create stats.json
        stats_path = tmpdir / "stats.json"
        stats = {"total_skills": 500, "canonical_skills": 500, "repositories": 20, "curated_skills": 10}
        stats_path.write_text(json.dumps(stats))

        # Create README with manual claim outside markers
        readme_path = tmpdir / "README.md"
        readme_content = """# Test README

The largest collection with 999 skills! (manual claim - should be caught by wording lint)

<!-- atlas:stats:start -->
Old content
<!-- atlas:stats:end -->
"""
        readme_path.write_text(readme_content)

        # Update
        update_readme_stats(readme_path, stats_path)

        # Read result
        new_content = readme_path.read_text()

        # Manual claim should still be there (not modified by stats updater)
        assert "999 skills" in new_content
        # But the stats block should be correct
        assert "500" in new_content.split("<!-- atlas:stats:start -->")[1].split("<!-- atlas:stats:end -->")[0]
