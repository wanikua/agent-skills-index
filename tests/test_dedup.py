#!/usr/bin/env python3
"""Tests for exact deduplication (S2-2)."""

from datetime import datetime

import pytest

from tools.atlas import dedup


def test_cluster_by_content_hash():
    """Test clustering skills by content_hash."""
    skills = [
        {
            "id": "github.com/test/repo1/skill1",
            "hashes": {"content_hash": "sha256:aaa"},
        },
        {
            "id": "github.com/test/repo2/skill2",
            "hashes": {"content_hash": "sha256:aaa"},
        },
        {
            "id": "github.com/test/repo3/skill3",
            "hashes": {"content_hash": "sha256:bbb"},
        },
    ]

    clusters = dedup.cluster_by_content_hash(skills)

    assert len(clusters) == 2
    assert len(clusters["sha256:aaa"]) == 2
    assert len(clusters["sha256:bbb"]) == 1


def test_select_canonical_single_skill():
    """Test that a single skill is selected as canonical."""
    cluster = [{"id": "github.com/test/repo/skill", "trust_tier": "community"}]

    canonical = dedup.select_canonical(cluster)

    assert canonical["id"] == "github.com/test/repo/skill"


def test_select_canonical_official_priority():
    """Test that official trust tier has priority."""
    cluster = [
        {
            "id": "github.com/anthropics/skills/skills/docx",
            "trust_tier": "official",
            "first_seen": "2026-09-20T00:00:00Z",
        },
        {
            "id": "github.com/composiohq/skills/docx",
            "trust_tier": "aggregator-copy",
            "first_seen": "2026-09-10T00:00:00Z",  # Earlier but not official
        },
    ]

    canonical = dedup.select_canonical(cluster)

    # Official skill should be canonical even though it's not earliest
    assert canonical["id"] == "github.com/anthropics/skills/skills/docx"


def test_select_canonical_earliest_first_seen():
    """Test that earliest first_seen wins when trust_tier is equal."""
    cluster = [
        {
            "id": "github.com/test/repo1/skill",
            "trust_tier": "community",
            "first_seen": "2026-09-20T00:00:00Z",
        },
        {
            "id": "github.com/test/repo2/skill",
            "trust_tier": "community",
            "first_seen": "2026-09-10T00:00:00Z",
        },
    ]

    canonical = dedup.select_canonical(cluster)

    # Earlier skill should be canonical
    assert canonical["id"] == "github.com/test/repo2/skill"


def test_select_canonical_alphabetical_tiebreaker():
    """Test alphabetical ID as final tie-breaker."""
    cluster = [
        {
            "id": "github.com/test/zebra/skill",
            "trust_tier": "community",
            "first_seen": "2026-09-20T00:00:00Z",
        },
        {
            "id": "github.com/test/alpha/skill",
            "trust_tier": "community",
            "first_seen": "2026-09-20T00:00:00Z",
        },
    ]

    canonical = dedup.select_canonical(cluster)

    # Alphabetically first should be canonical
    assert canonical["id"] == "github.com/test/alpha/skill"


def test_apply_deduplication_no_duplicates():
    """Test deduplication with no duplicates."""
    skills = [
        {
            "id": "github.com/test/repo1/skill1",
            "hashes": {"content_hash": "sha256:aaa"},
            "trust_tier": "community",
            "dedup": {},
        },
        {
            "id": "github.com/test/repo2/skill2",
            "hashes": {"content_hash": "sha256:bbb"},
            "trust_tier": "community",
            "dedup": {},
        },
    ]

    result = dedup.apply_deduplication(skills)

    assert len(result) == 2
    # Both should be marked as canonical
    assert result[0]["dedup"]["canonical_id"] == result[0]["id"]
    assert result[1]["dedup"]["canonical_id"] == result[1]["id"]
    assert "duplicate_of" not in result[0]["dedup"]
    assert "duplicate_of" not in result[1]["dedup"]


def test_apply_deduplication_with_duplicates():
    """Test deduplication with duplicate skills."""
    skills = [
        {
            "id": "github.com/test/repo1/skill",
            "hashes": {"content_hash": "sha256:aaa"},
            "trust_tier": "community",
            "first_seen": "2026-09-10T00:00:00Z",
            "dedup": {},
        },
        {
            "id": "github.com/test/repo2/skill",
            "hashes": {"content_hash": "sha256:aaa"},
            "trust_tier": "aggregator-copy",
            "first_seen": "2026-09-20T00:00:00Z",
            "dedup": {},
        },
    ]

    result = dedup.apply_deduplication(skills)

    assert len(result) == 2

    # Find canonical and duplicate
    canonical = None
    duplicate = None
    for skill in result:
        if skill["id"] == "github.com/test/repo1/skill":
            canonical = skill
        else:
            duplicate = skill

    # Check canonical
    assert canonical["dedup"]["canonical_id"] == canonical["id"]
    assert "duplicate_of" not in canonical["dedup"]

    # Check duplicate
    assert duplicate["dedup"]["duplicate_of"] == canonical["id"]
    assert duplicate["trust_tier"] == "aggregator-copy"


def test_anthropics_docx_dedup_case():
    """
    Test the anthropics docx skill and its copies collapse to ONE cluster.

    This is the main acceptance criterion from PLAN.md S2-2:
    "Tests covering: anthropics `docx` and the three copies in ComposioHQ /
    K-Dense / sickn33 collapse to ONE cluster whose canonical points at anthropics."
    """
    # Create fixture skills based on the real scenario
    # All four skills have the same content (thus same content_hash)
    content_hash = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    skills = [
        {
            "id": "github.com/anthropics/skills/skills/docx",
            "name": "docx",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "official",
            "first_seen": "2026-09-15T00:00:00Z",
            "source": {"source_id": "anthropic-skills"},
            "dedup": {},
        },
        {
            "id": "github.com/composiohq/agent-skills/docx",
            "name": "docx",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "aggregator-copy",
            "first_seen": "2026-09-20T00:00:00Z",
            "source": {"source_id": "composiohq-skills"},
            "dedup": {},
        },
        {
            "id": "github.com/k-dense/skills-collection/skills/docx",
            "name": "docx",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "aggregator-copy",
            "first_seen": "2026-09-22T00:00:00Z",
            "source": {"source_id": "k-dense-skills"},
            "dedup": {},
        },
        {
            "id": "github.com/sickn33/awesome-skills/docx",
            "name": "docx",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "aggregator-copy",
            "first_seen": "2026-09-24T00:00:00Z",
            "source": {"source_id": "sickn33-skills"},
            "dedup": {},
        },
    ]

    # Apply deduplication
    result = dedup.apply_deduplication(skills)

    assert len(result) == 4

    # Check clustering
    clusters = dedup.cluster_by_content_hash(result)
    assert len(clusters) == 1  # All four should be in one cluster
    assert len(clusters[content_hash]) == 4

    # Find the canonical skill
    canonical_skills = [s for s in result if s["dedup"].get("canonical_id") == s["id"]]
    assert len(canonical_skills) == 1

    canonical = canonical_skills[0]
    # The canonical should be the anthropics one (official trust tier)
    assert canonical["id"] == "github.com/anthropics/skills/skills/docx"
    assert canonical["trust_tier"] == "official"

    # Check duplicates
    duplicates = [s for s in result if "duplicate_of" in s["dedup"]]
    assert len(duplicates) == 3

    for duplicate in duplicates:
        # All duplicates should point to anthropics as canonical
        assert duplicate["dedup"]["duplicate_of"] == "github.com/anthropics/skills/skills/docx"
        # All should be marked as aggregator-copy
        assert duplicate["trust_tier"] == "aggregator-copy"


def test_compute_canonical_count():
    """Test counting canonical skills."""
    skills = [
        {"id": "skill1", "dedup": {"canonical_id": "skill1"}},
        {"id": "skill2", "dedup": {"canonical_id": "skill2"}},
        {"id": "skill3", "dedup": {"duplicate_of": "skill1"}},
        {"id": "skill4", "dedup": {"duplicate_of": "skill2"}},
    ]

    count = dedup.compute_canonical_count(skills)

    # Only skill1 and skill2 are canonical
    assert count == 2


def test_multiple_official_sources_earliest_wins():
    """Test that when multiple official sources exist, earliest wins."""
    content_hash = "sha256:test"

    skills = [
        {
            "id": "github.com/vendor1/skills/skill",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "official",
            "first_seen": "2026-09-20T00:00:00Z",
            "dedup": {},
        },
        {
            "id": "github.com/vendor2/skills/skill",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "official",
            "first_seen": "2026-09-10T00:00:00Z",  # Earlier
            "dedup": {},
        },
    ]

    result = dedup.apply_deduplication(skills)

    # Find canonical
    canonical = [s for s in result if s["dedup"].get("canonical_id") == s["id"]][0]

    # The earlier vendor2 should be canonical
    assert canonical["id"] == "github.com/vendor2/skills/skill"


def test_dedup_preserves_other_fields():
    """Test that deduplication doesn't modify unrelated fields."""
    skills = [
        {
            "id": "github.com/test/repo/skill",
            "name": "test-skill",
            "description": "A test skill",
            "hashes": {"content_hash": "sha256:unique"},
            "trust_tier": "community",
            "license": {"class": "allow"},
            "dedup": {},
        }
    ]

    result = dedup.apply_deduplication(skills)

    # Check that other fields are preserved
    assert result[0]["name"] == "test-skill"
    assert result[0]["description"] == "A test skill"
    assert result[0]["license"]["class"] == "allow"
    assert result[0]["trust_tier"] == "community"


def test_empty_skills_list():
    """Test deduplication with empty skills list."""
    skills = []
    result = dedup.apply_deduplication(skills)
    assert result == []


def test_parse_iso_datetime():
    """Test ISO datetime parsing."""
    # Valid timestamps
    ts1 = dedup.parse_iso_datetime("2026-09-24T00:00:00Z")
    assert isinstance(ts1, datetime)

    ts2 = dedup.parse_iso_datetime("2026-09-24T12:34:56.789Z")
    assert isinstance(ts2, datetime)

    ts3 = dedup.parse_iso_datetime("2026-09-24T12:34:56+00:00")
    assert isinstance(ts3, datetime)

    # Invalid timestamps
    assert dedup.parse_iso_datetime(None) is None
    assert dedup.parse_iso_datetime("invalid") is None
    assert dedup.parse_iso_datetime("") is None


def test_tier_3_skills_become_aggregator_copy():
    """Test that tier 3 duplicates are marked as aggregator-copy."""
    content_hash = "sha256:test"

    skills = [
        {
            "id": "github.com/original/repo/skill",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "community",
            "first_seen": "2026-09-10T00:00:00Z",
            "dedup": {},
        },
        {
            "id": "github.com/aggregator/repo/skill",
            "hashes": {"content_hash": content_hash},
            "trust_tier": "unreviewed",  # Tier 3
            "first_seen": "2026-09-20T00:00:00Z",
            "dedup": {},
        },
    ]

    result = dedup.apply_deduplication(skills)

    # Find the duplicate
    duplicate = [s for s in result if "duplicate_of" in s["dedup"]][0]

    # Should be marked as aggregator-copy
    assert duplicate["trust_tier"] == "aggregator-copy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
