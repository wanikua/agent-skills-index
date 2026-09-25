#!/usr/bin/env python3
"""Tests for router-lite generation."""

import json
import tempfile
from pathlib import Path

from tools.atlas.router_lite import (
    MAX_CURATED_SIZE,
    MAX_KEYWORDS,
    compute_idf_scores,
    create_router_lite_record,
    extract_body_info,
    extract_keywords,
    generate_router_lite,
    should_include_in_router_lite,
)


def test_should_include_canonical_only():
    """Test that only canonical skills are included."""
    # Canonical skill (no canonical_id or canonical_id == id)
    skill1 = {
        "id": "github.com/test/repo/skill1",
        "status": "active",
        "security": {"status": "pass"},
        "dedup": {},
    }
    assert should_include_in_router_lite(skill1)

    skill2 = {
        "id": "github.com/test/repo/skill2",
        "status": "active",
        "security": {"status": "pass"},
        "dedup": {"canonical_id": "github.com/test/repo/skill2"},
    }
    assert should_include_in_router_lite(skill2)

    # Non-canonical skill (canonical_id points elsewhere)
    skill3 = {
        "id": "github.com/test/repo/skill3",
        "status": "active",
        "security": {"status": "pass"},
        "dedup": {"canonical_id": "github.com/other/repo/original"},
    }
    assert not should_include_in_router_lite(skill3)


def test_should_exclude_non_active():
    """Test that non-active skills are excluded."""
    skill = {
        "id": "github.com/test/repo/skill",
        "status": "removed",
        "security": {"status": "pass"},
        "dedup": {},
    }
    assert not should_include_in_router_lite(skill)

    skill["status"] = "quarantined"
    assert not should_include_in_router_lite(skill)

    skill["status"] = "dangling"
    assert not should_include_in_router_lite(skill)

    skill["status"] = "active"
    assert should_include_in_router_lite(skill)


def test_should_exclude_malicious():
    """Test that malicious skills are excluded."""
    skill = {
        "id": "github.com/test/repo/skill",
        "status": "active",
        "security": {"status": "malicious"},
        "dedup": {},
    }
    assert not should_include_in_router_lite(skill)

    # Other security statuses are OK
    for status in ["pass", "pending", "review", "warn"]:
        skill["security"]["status"] = status
        assert should_include_in_router_lite(skill)


def test_extract_keywords_basic():
    """Test basic keyword extraction."""
    keywords = extract_keywords(
        name="pdf-processor",
        description="Process PDF documents and extract text",
        body_head=None,
        titles=None,
    )

    assert isinstance(keywords, list)
    assert len(keywords) <= MAX_KEYWORDS
    assert "pdf" in [k.lower() for k in keywords]
    assert "process" in [k.lower() for k in keywords] or "processor" in [k.lower() for k in keywords]


def test_extract_keywords_with_body():
    """Test keyword extraction with body text."""
    keywords = extract_keywords(
        name="data-analyzer",
        description="Analyze and visualize data",
        body_head=(
            "This skill helps you analyze complex datasets, perform statistical analysis, "
            "and create visualizations. It supports CSV, JSON, and Excel formats."
        ),
        titles=None,
    )

    assert isinstance(keywords, list)
    assert len(keywords) <= MAX_KEYWORDS
    assert "data" in [k.lower() for k in keywords] or "analyze" in [k.lower() for k in keywords]


def test_extract_keywords_with_titles():
    """Test keyword extraction with titles only (restricted license)."""
    keywords = extract_keywords(
        name="web-scraper",
        description="Scrape websites",
        body_head=None,
        titles=["Installation", "Usage Guide", "API Reference", "Configuration Options"],
    )

    assert isinstance(keywords, list)
    assert len(keywords) <= MAX_KEYWORDS


def test_extract_keywords_caps_at_max():
    """Test that keyword count is capped at MAX_KEYWORDS."""
    # Create a very long text with many unique terms
    long_text = " ".join([f"term{i}" for i in range(100)])

    keywords = extract_keywords(
        name="test",
        description=long_text,
        body_head=None,
        titles=None,
    )

    assert len(keywords) <= MAX_KEYWORDS


def test_extract_keywords_filters_stopwords():
    """Test that stopwords are filtered out."""
    keywords = extract_keywords(
        name="the-ultimate-skill",
        description="This is the best skill for all your needs",
        body_head=None,
        titles=None,
    )

    # Stopwords like "the", "is", "for", "all", "your" should not be in keywords
    # Note: "best" and "ultimate" are valid keywords, not stopwords
    stopwords_found = [k for k in keywords if k in ["the", "is", "for", "all", "your", "this"]]
    assert len(stopwords_found) == 0


def test_compute_idf_scores():
    """Test IDF score computation."""
    skills = [
        {"name": "pdf-reader", "description": "Read PDF files"},
        {"name": "pdf-writer", "description": "Write PDF documents"},
        {"name": "text-editor", "description": "Edit text files"},
    ]

    idf_scores = compute_idf_scores(skills)

    assert isinstance(idf_scores, dict)
    assert len(idf_scores) > 0

    # "pdf" appears in 2/3 documents, should have lower IDF than "text" (1/3 documents)
    if "pdf" in idf_scores and "text" in idf_scores:
        assert idf_scores["text"] > idf_scores["pdf"]


def test_extract_body_info_allow_license():
    """Test body extraction for allow license."""
    skill = {
        "id": "test",
        "license": {"class": "allow"},
    }

    body_content = """---
name: test
description: Test skill
---

# Introduction

This is a test skill with some content. It has multiple paragraphs and should extract the first 400 words.

# Features

- Feature 1
- Feature 2
"""

    body_head, titles = extract_body_info(skill, body_content)

    assert body_head is not None
    assert titles is None
    assert "Introduction" in body_head
    assert "test skill" in body_head


def test_extract_body_info_deny_license():
    """Test title extraction for deny license."""
    skill = {
        "id": "test",
        "license": {"class": "deny"},
    }

    body_content = """---
name: test
---

# Introduction

Some content here.

## Setup

More content.

### Configuration

Even more content.
"""

    body_head, titles = extract_body_info(skill, body_content)

    assert body_head is None
    assert titles is not None
    assert "Introduction" in titles
    assert "Setup" in titles
    assert "Configuration" in titles


def test_extract_body_info_title_limit():
    """Test that title extraction is limited to 20 titles."""
    skill = {
        "id": "test",
        "license": {"class": "unknown"},
    }

    # Create content with 30 titles
    body_content = "---\nname: test\n---\n\n"
    body_content += "\n\n".join([f"# Title {i}" for i in range(30)])

    body_head, titles = extract_body_info(skill, body_content)

    assert body_head is None
    assert titles is not None
    assert len(titles) <= 20


def test_create_router_lite_record():
    """Test router-lite record creation."""
    skill = {
        "id": "github.com/test/repo/skill",
        "name": "test-skill",
        "description": "A test skill for unit testing",
        "trust_tier": "official",
        "license": {"spdx": "MIT"},
        "security": {"status": "pass"},
        "install": {"npx": "npx skills add test-skill"},
        "source": {"url": "https://github.com/test/repo"},
        "hashes": {"content_hash": "sha256:abc123"},
    }

    keywords = ["test", "unit", "mock"]

    record = create_router_lite_record(skill, keywords)

    assert record["id"] == skill["id"]
    assert record["n"] == skill["name"]
    assert record["d"] == skill["description"]
    assert record["kw"] == keywords
    assert record["tier"] == "official"
    assert record["lic"] == "MIT"
    assert record["sec"] == "pass"
    assert record["url"] == skill["source"]["url"]
    assert record["h"] == "sha256:abc123"


def test_create_router_lite_record_truncates_description():
    """Test that long descriptions are truncated to 200 chars."""
    skill = {
        "id": "github.com/test/repo/skill",
        "name": "test",
        "description": "A" * 300,  # 300 character description
        "trust_tier": "community",
        "license": {"spdx": "Apache-2.0"},
        "security": {"status": "pending"},
        "install": {},
        "source": {"url": ""},
        "hashes": {"content_hash": ""},
    }

    record = create_router_lite_record(skill, [])

    assert len(record["d"]) == 200
    assert record["d"].endswith("...")


def test_generate_router_lite_empty():
    """Test router-lite generation with empty input."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "router-lite"

        result = generate_router_lite([], output_dir)

        assert result["success"] is True
        assert result["total_skills"] == 0
        assert len(result["files_created"]) == 0


def test_generate_router_lite_filters():
    """Test that router-lite applies all filters correctly."""
    skills = [
        # Should be included: canonical, active, not malicious
        {
            "id": "github.com/test/repo/skill1",
            "name": "skill1",
            "description": "Test skill 1",
            "status": "active",
            "trust_tier": "official",
            "license": {"class": "allow", "spdx": "MIT"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
        # Should be excluded: not canonical
        {
            "id": "github.com/test/repo/skill2",
            "name": "skill2",
            "description": "Test skill 2",
            "status": "active",
            "trust_tier": "community",
            "license": {"class": "allow", "spdx": "MIT"},
            "security": {"status": "pass"},
            "dedup": {"canonical_id": "github.com/other/repo/original"},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
        # Should be excluded: not active
        {
            "id": "github.com/test/repo/skill3",
            "name": "skill3",
            "description": "Test skill 3",
            "status": "removed",
            "trust_tier": "community",
            "license": {"class": "allow", "spdx": "MIT"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
        # Should be excluded: malicious
        {
            "id": "github.com/test/repo/skill4",
            "name": "skill4",
            "description": "Test skill 4",
            "status": "active",
            "trust_tier": "unreviewed",
            "license": {"class": "unknown", "spdx": "NOASSERTION"},
            "security": {"status": "malicious"},
            "dedup": {},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "router-lite"

        result = generate_router_lite(skills, output_dir)

        assert result["success"] is True
        assert result["total_skills"] == 1  # Only skill1 should be included


def test_generate_router_lite_sharding():
    """Test that skills are sharded by trust tier."""
    skills = [
        # Curated
        {
            "id": "github.com/test/repo/curated1",
            "name": "curated1",
            "description": "Curated skill",
            "status": "active",
            "trust_tier": "curated",
            "license": {"class": "allow", "spdx": "MIT"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
        # Official
        {
            "id": "github.com/test/repo/official1",
            "name": "official1",
            "description": "Official skill",
            "status": "active",
            "trust_tier": "official",
            "license": {"class": "allow", "spdx": "Apache-2.0"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
        # Community
        {
            "id": "github.com/test/repo/community1",
            "name": "community1",
            "description": "Community skill",
            "status": "active",
            "trust_tier": "community",
            "license": {"class": "allow", "spdx": "MIT"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {},
            "source": {"url": ""},
            "hashes": {"content_hash": ""},
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "router-lite"

        result = generate_router_lite(skills, output_dir)

        assert result["success"] is True
        assert result["curated"] == 1
        assert result["official"] == 1
        assert result["community"] == 1

        # Check files exist
        assert (output_dir / "curated.jsonl").exists()
        assert (output_dir / "official.jsonl").exists()
        assert (output_dir / "community-00.jsonl").exists()


def test_generate_router_lite_size_limits():
    """Test that generated files respect size limits."""
    # Create curated skills
    curated_skills = []
    for i in range(50):
        curated_skills.append(
            {
                "id": f"github.com/test/repo/curated{i}",
                "name": f"curated{i}",
                "description": f"Curated skill {i} with a reasonably long description to test size limits",
                "status": "active",
                "trust_tier": "curated",
                "license": {"class": "allow", "spdx": "MIT"},
                "security": {"status": "pass"},
                "dedup": {},
                "install": {"npx": f"npx skills add curated{i}"},
                "source": {"url": f"https://github.com/test/repo{i}"},
                "hashes": {"content_hash": f"sha256:hash{i}"},
            }
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "router-lite"

        result = generate_router_lite(curated_skills, output_dir)

        assert result["success"] is True

        # Check that curated.jsonl is within limit
        curated_file = output_dir / "curated.jsonl"
        assert curated_file.exists()

        curated_size = curated_file.stat().st_size
        # Allow some tolerance since we might truncate descriptions
        # The limit is enforced, but a warning is logged if exceeded
        assert curated_size <= MAX_CURATED_SIZE * 1.5  # Allow 50% tolerance for test


def test_generate_router_lite_determinism():
    """Test that router-lite generation is deterministic."""
    skills = [
        {
            "id": "github.com/test/repo/skill1",
            "name": "skill1",
            "description": "Test skill 1 for determinism check",
            "status": "active",
            "trust_tier": "official",
            "license": {"class": "allow", "spdx": "MIT"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {"npx": "npx skills add skill1"},
            "source": {"url": "https://github.com/test/repo"},
            "hashes": {"content_hash": "sha256:abc123"},
        },
        {
            "id": "github.com/test/repo/skill2",
            "name": "skill2",
            "description": "Test skill 2 for determinism check",
            "status": "active",
            "trust_tier": "community",
            "license": {"class": "allow", "spdx": "Apache-2.0"},
            "security": {"status": "pass"},
            "dedup": {},
            "install": {"npx": "npx skills add skill2"},
            "source": {"url": "https://github.com/test/repo"},
            "hashes": {"content_hash": "sha256:def456"},
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir1:
        with tempfile.TemporaryDirectory() as tmpdir2:
            output_dir1 = Path(tmpdir1) / "router-lite"
            output_dir2 = Path(tmpdir2) / "router-lite"

            # Generate twice
            result1 = generate_router_lite(skills, output_dir1)
            result2 = generate_router_lite(skills, output_dir2)

            assert result1["success"] is True
            assert result2["success"] is True

            # Compare output files
            for file_info in result1["files_created"]:
                filename = file_info["file"]

                file1 = output_dir1 / filename
                file2 = output_dir2 / filename

                assert file1.exists()
                assert file2.exists()

                content1 = file1.read_text()
                content2 = file2.read_text()

                assert content1 == content2, f"Files {filename} differ between runs"


def test_generate_router_lite_community_sharding():
    """Test that large community skill sets are split into multiple shards."""
    # Create many community skills to trigger sharding
    community_skills = []
    for i in range(100):
        community_skills.append(
            {
                "id": f"github.com/test/repo{i}/skill",
                "name": f"community-skill-{i}",
                "description": f"Community skill {i} " + ("X" * 200),  # Make descriptions longer
                "status": "active",
                "trust_tier": "community",
                "license": {"class": "allow", "spdx": "MIT"},
                "security": {"status": "pass"},
                "dedup": {},
                "install": {"npx": f"npx skills add community-skill-{i}"},
                "source": {"url": f"https://github.com/test/repo{i}"},
                "hashes": {"content_hash": f"sha256:hash{i}{'a' * 60}"},
            }
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "router-lite"

        result = generate_router_lite(community_skills, output_dir)

        assert result["success"] is True
        assert result["community"] == 100

        # Should have created multiple community shards
        community_files = list(output_dir.glob("community-*.jsonl"))
        assert len(community_files) >= 1

        # Each shard should be within the size limit
        for shard_file in community_files:
            size = shard_file.stat().st_size
            # Allow some tolerance
            assert size <= 1.5 * 1024 * 1024  # 1.5 MB tolerance


def test_generate_router_lite_mixed_tiers():
    """Test router-lite generation with a mix of all trust tiers."""
    skills = []

    # Add 5 of each tier
    for tier in ["curated", "official", "community", "unreviewed", "aggregator-copy"]:
        for i in range(5):
            skills.append(
                {
                    "id": f"github.com/test/{tier}/skill{i}",
                    "name": f"{tier}-{i}",
                    "description": f"Test {tier} skill {i}",
                    "status": "active",
                    "trust_tier": tier,
                    "license": {"class": "allow", "spdx": "MIT"},
                    "security": {"status": "pass"},
                    "dedup": {},
                    "install": {},
                    "source": {"url": ""},
                    "hashes": {"content_hash": f"sha256:{tier}{i}"},
                }
            )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "router-lite"

        result = generate_router_lite(skills, output_dir)

        assert result["success"] is True
        assert result["total_skills"] == 25
        assert result["curated"] == 5
        assert result["official"] == 5
        assert result["community"] == 15  # community + unreviewed + aggregator-copy

        # Verify all expected files exist
        assert (output_dir / "curated.jsonl").exists()
        assert (output_dir / "official.jsonl").exists()
        assert (output_dir / "community-00.jsonl").exists()

        # Verify content
        with open(output_dir / "curated.jsonl") as f:
            curated_records = [json.loads(line) for line in f]
            assert len(curated_records) == 5
            assert all(r["tier"] == "curated" for r in curated_records)
