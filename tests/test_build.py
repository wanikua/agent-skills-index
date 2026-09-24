#!/usr/bin/env python3
"""Tests for the build command."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from tools.atlas import build, crawl


def create_test_crawl_output(tmpdir: Path) -> tuple[Path, Path]:
    """
    Create test crawl output files.

    Returns:
        (raw_dir, sources_file)
    """
    raw_dir = tmpdir / "build" / "raw"
    raw_dir.mkdir(parents=True)

    # Create a test source
    sources_file = tmpdir / "index" / "sources.json"
    sources_file.parent.mkdir(parents=True)

    sources_data = {
        "schema_version": "2.0.0",
        "generated_at": "2026-09-24T00:00:00Z",
        "description": "Test sources",
        "total_repositories": 2,
        "repositories": [
            {
                "id": "test-vendor",
                "url": "https://github.com/testvendor/skills",
                "owner_type": "vendor",
                "tier": 1,
                "status": "active",
                "added_at": "2026-09-24T00:00:00Z",
                "last_crawled_commit": None,
                "last_crawled_at": None,
                "verified": False,
                "include_patterns": ["skills/*/SKILL.md"],
            },
            {
                "id": "test-community",
                "url": "https://github.com/testcommunity/skills",
                "owner_type": "individual",
                "tier": 2,
                "status": "active",
                "added_at": "2026-09-24T00:00:00Z",
                "last_crawled_commit": None,
                "last_crawled_at": None,
                "verified": False,
                "include_patterns": ["*/SKILL.md"],
            },
        ],
    }

    with open(sources_file, "w", encoding="utf-8") as f:
        json.dump(sources_data, f, indent=2)

    # Create test crawl output for vendor skill
    vendor_skill = {
        "source_id": "test-vendor",
        "path": "skills/test-skill/SKILL.md",
        "skill_dir": "skills/test-skill",
        "blob_sha": "a" * 40,
        "content": """---
name: test-skill
description: A test skill for unit testing
license: MIT
---

# Test Skill

This is a test skill for verification.
""",
        "skill_md_sha256": "b" * 64,
        "folder_sha256": "c" * 64,
        "has_scripts": False,
        "license_files": ["skills/test-skill/LICENSE"],
        "conformance_errors": [],
        "crawled_at": "2026-09-24T00:00:00Z",
        "commit_sha": "d" * 40,
    }

    # Create test crawl output for community skill
    community_skill = {
        "source_id": "test-community",
        "path": "my-skill/SKILL.md",
        "skill_dir": "my-skill",
        "blob_sha": "e" * 40,
        "content": """---
name: my-skill
description: Another test skill
license: Apache-2.0
---

# My Skill

Community contributed skill.
""",
        "skill_md_sha256": "f" * 64,
        "folder_sha256": "g" * 64,
        "has_scripts": True,
        "license_files": ["LICENSE"],
        "conformance_errors": [],
        "crawled_at": "2026-09-24T00:00:00Z",
        "commit_sha": "h" * 40,
    }

    # Write crawl outputs
    with open(raw_dir / "test-vendor.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(vendor_skill) + "\n")

    with open(raw_dir / "test-community.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(community_skill) + "\n")

    return raw_dir, sources_file


def test_build_creates_output_files():
    """Test that build creates all required output files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        result = build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        assert result["success"]
        assert result["skills_built"] == 2

        # Check that all output files exist
        assert (index_dir / "skills.jsonl").exists()
        assert (index_dir / "skills.json").exists()
        assert (index_dir / "stats.json").exists()
        assert (index_dir / "changes.jsonl").exists()


def test_build_determinism():
    """Test that two consecutive builds produce identical output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        # First build
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Read first build outputs
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            skills_1 = f.read()
        with open(index_dir / "skills.json", encoding="utf-8") as f:
            skills_json_1 = json.load(f)
        with open(index_dir / "stats.json", encoding="utf-8") as f:
            stats_1 = json.load(f)

        # Second build
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Read second build outputs
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            skills_2 = f.read()
        with open(index_dir / "skills.json", encoding="utf-8") as f:
            skills_json_2 = json.load(f)
        with open(index_dir / "stats.json", encoding="utf-8") as f:
            stats_2 = json.load(f)

        # Compare skills.jsonl (should be identical except timestamps)
        skills_1_lines = [json.loads(line) for line in skills_1.strip().split("\n")]
        skills_2_lines = [json.loads(line) for line in skills_2.strip().split("\n")]

        assert len(skills_1_lines) == len(skills_2_lines)

        # For each skill, timestamps should be preserved
        for s1, s2 in zip(skills_1_lines, skills_2_lines):
            assert s1["id"] == s2["id"]
            assert s1["first_seen"] == s2["first_seen"]  # Should be same
            assert s1["hashes"] == s2["hashes"]  # Should be identical

        # Stats should be identical except for generated_at
        assert stats_1["total_skills"] == stats_2["total_skills"]
        assert stats_1["by_license_class"] == stats_2["by_license_class"]
        assert stats_1["by_trust_tier"] == stats_2["by_trust_tier"]


def test_stats_recomputable_from_skills():
    """Test that stats.json can be recomputed from skills.jsonl."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        result = build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load skills.jsonl
        skills = []
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            for line in f:
                skills.append(json.loads(line))

        # Load stats.json
        with open(index_dir / "stats.json", encoding="utf-8") as f:
            stats = json.load(f)

        # Recompute stats
        assert stats["total_skills"] == len(skills)
        assert stats["curated_skills"] == sum(1 for s in skills if s.get("layer") == "curated")
        assert stats["repositories"] == 2

        # Check license class counts
        license_counts = {}
        for skill in skills:
            lic_class = skill.get("license", {}).get("class", "unknown")
            license_counts[lic_class] = license_counts.get(lic_class, 0) + 1

        for lic_class, count in license_counts.items():
            assert stats["by_license_class"].get(lic_class, 0) == count

        # Check trust tier counts
        tier_counts = {}
        for skill in skills:
            tier = skill.get("trust_tier", "unreviewed")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        for tier, count in tier_counts.items():
            assert stats["by_trust_tier"].get(tier, 0) == count

        # Check spec strict valid percentage
        strict_valid = sum(1 for s in skills if s.get("conformance", {}).get("strict", False))
        expected_pct = round((strict_valid / len(skills) * 100), 2) if skills else 0.0
        assert stats["spec_strict_valid_pct"] == expected_pct


def test_trust_tier_assignment():
    """Test that trust tiers are assigned correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load skills
        skills = []
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            for line in f:
                skills.append(json.loads(line))

        # Find vendor skill
        vendor_skill = [s for s in skills if "testvendor" in s["id"]][0]
        assert vendor_skill["trust_tier"] == "official"

        # Find community skill
        community_skill = [s for s in skills if "testcommunity" in s["id"]][0]
        assert community_skill["trust_tier"] == "community"


def test_skill_id_format():
    """Test that skill IDs follow the correct format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load skills
        skills = []
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            for line in f:
                skills.append(json.loads(line))

        # Check ID format
        for skill in skills:
            assert skill["id"].startswith("github.com/")
            assert "/" in skill["id"][11:]  # Should have at least owner/repo/path


def test_changes_jsonl_tracks_additions():
    """Test that changes.jsonl tracks new skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        # First build
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Check changes
        with open(index_dir / "changes.jsonl", encoding="utf-8") as f:
            changes = [json.loads(line) for line in f]

        # Should have 2 additions
        additions = [c for c in changes if c["type"] == "added"]
        assert len(additions) == 2


def test_normalize_content_for_hash():
    """Test content normalization for hash computation."""
    # Test BOM removal
    content_with_bom = "\ufeff---\nname: test\n---\n"
    normalized = build.normalize_content_for_hash(content_with_bom)
    assert not normalized.startswith("\ufeff")

    # Test CRLF -> LF
    content_crlf = "---\r\nname: test\r\n---\r\n"
    normalized = build.normalize_content_for_hash(content_crlf)
    assert "\r\n" not in normalized

    # Test trailing whitespace removal
    content_trailing = "---\nname: test  \n---\nContent  \n"
    normalized = build.normalize_content_for_hash(content_trailing)
    lines = normalized.split("\n")
    for line in lines[:-1]:  # Except last empty line
        if line:
            assert not line.endswith(" ")

    # Test single trailing newline
    content_no_newline = "test"
    normalized = build.normalize_content_for_hash(content_no_newline)
    assert normalized.endswith("\n")
    assert not normalized.endswith("\n\n")


def test_content_hash_consistency():
    """Test that content hash is consistent for same content."""
    content = """---
name: test
description: Test skill
---

# Test
"""

    fm = {"name": "test", "description": "Test skill"}

    hash1 = build.compute_content_hash(content, fm)
    hash2 = build.compute_content_hash(content, fm)

    assert hash1 == hash2
    assert hash1.startswith("sha256:")


def test_timestamp_inheritance():
    """Test that timestamps are inherited from existing records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        # First build
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load first build
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            skills_1 = [json.loads(line) for line in f]

        first_seen_original = skills_1[0]["first_seen"]

        # Second build (simulating a later time)
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load second build
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            skills_2 = [json.loads(line) for line in f]

        # first_seen should be preserved
        assert skills_2[0]["first_seen"] == first_seen_original


def test_removed_skills_marked():
    """Test that removed skills are marked with status: removed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        # First build with 2 skills
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Remove one skill from crawl output
        (raw_dir / "test-community.jsonl").unlink()

        # Second build
        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load skills
        with open(index_dir / "skills.jsonl", encoding="utf-8") as f:
            skills = [json.loads(line) for line in f]

        # Should still have 2 skills (one active, one removed)
        assert len(skills) == 2

        # Find the removed skill
        removed_skills = [s for s in skills if s["status"] == "removed"]
        assert len(removed_skills) == 1
        assert "testcommunity" in removed_skills[0]["id"]

        # Check changes.jsonl
        with open(index_dir / "changes.jsonl", encoding="utf-8") as f:
            changes = [json.loads(line) for line in f]

        removals = [c for c in changes if c["type"] == "removed"]
        assert len(removals) == 1


def test_skills_json_wrapper_format():
    """Test that skills.json follows the wrapper format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir, sources_file = create_test_crawl_output(tmpdir)
        index_dir = tmpdir / "index"

        build.build_index(raw_dir, sources_file, index_dir, tmpdir)

        # Load skills.json
        with open(index_dir / "skills.json", encoding="utf-8") as f:
            wrapper = json.load(f)

        # Check required fields
        assert "schema_version" in wrapper
        assert wrapper["schema_version"] == "2.0.0"
        assert "generated_at" in wrapper
        assert "description" in wrapper
        assert "total_count" in wrapper
        assert "curated_count" in wrapper
        assert "skills" in wrapper

        # Check that skills array contains valid records
        assert len(wrapper["skills"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
