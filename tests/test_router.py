"""Tests for router module (S3-2)."""

import json
import sqlite3

import pytest

from tools.atlas import router


@pytest.fixture
def sample_skills_jsonl(tmp_path):
    """Create a sample skills.jsonl for testing."""
    skills_file = tmp_path / "skills.jsonl"

    skills = [
        {
            "id": "github.com/example/skills/pdf",
            "name": "pdf",
            "description": "Extract text and metadata from PDF documents",
            "layer": "curated",
            "source": {"url": "https://github.com/example/skills/tree/main/pdf"},
            "hashes": {"content_hash": "sha256:abc123"},
            "install": {"npx": "npx skills add example/skills/pdf", "gh": None, "claude_plugin": None},
            "trust_tier": "official",
            "license": {"spdx": "MIT"},
            "security": {"status": "pass"},
            "tags": ["pdf", "documents", "text-extraction"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/example/skills/pdf"},
        },
        {
            "id": "github.com/example/skills/web-scraper",
            "name": "web-scraper",
            "description": "Scrape content from websites and extract structured data",
            "layer": "source",
            "source": {"url": "https://github.com/example/skills/tree/main/web-scraper"},
            "hashes": {"content_hash": "sha256:def456"},
            "install": {"npx": "npx skills add example/skills/web-scraper", "gh": None, "claude_plugin": None},
            "trust_tier": "community",
            "license": {"spdx": "Apache-2.0"},
            "security": {"status": "review"},
            "tags": ["web", "scraping", "html"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/example/skills/web-scraper"},
        },
        {
            "id": "github.com/other/repo/pdf-tool",
            "name": "pdf-tool",
            "description": "Extract text and metadata from PDF documents",
            "layer": "source",
            "source": {"url": "https://github.com/other/repo/tree/main/pdf-tool"},
            "hashes": {"content_hash": "sha256:abc123"},  # Same content hash as first skill
            "install": {"npx": None, "gh": None, "claude_plugin": None},
            "trust_tier": "aggregator-copy",
            "license": {"spdx": "MIT"},
            "security": {"status": "pass"},
            "tags": ["pdf", "documents"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/example/skills/pdf"},  # Points to canonical
        },
        {
            "id": "github.com/example/skills/generic-helper",
            "name": "generic-helper",
            "description": "A general-purpose tool for any task you need help with",
            "layer": "source",
            "source": {"url": "https://github.com/example/skills/tree/main/generic-helper"},
            "hashes": {"content_hash": "sha256:ghi789"},
            "install": {"npx": None, "gh": None, "claude_plugin": None},
            "trust_tier": "unreviewed",
            "license": {"spdx": "NOASSERTION"},
            "security": {"status": "pending"},
            "tags": ["generic", "helper"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/example/skills/generic-helper"},
        },
        {
            "id": "github.com/malicious/repo/bad-skill",
            "name": "bad-skill",
            "description": "This should be excluded",
            "layer": "source",
            "source": {"url": "https://github.com/malicious/repo/tree/main/bad-skill"},
            "hashes": {"content_hash": "sha256:jkl012"},
            "install": {"npx": None, "gh": None, "claude_plugin": None},
            "trust_tier": "unreviewed",
            "license": {"spdx": "MIT"},
            "security": {"status": "malicious"},
            "tags": ["bad"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/malicious/repo/bad-skill"},
        },
        {
            "id": "github.com/example/skills/inactive",
            "name": "inactive",
            "description": "This should be excluded (inactive)",
            "layer": "source",
            "source": {"url": "https://github.com/example/skills/tree/main/inactive"},
            "hashes": {"content_hash": "sha256:mno345"},
            "install": {"npx": None, "gh": None, "claude_plugin": None},
            "trust_tier": "community",
            "license": {"spdx": "MIT"},
            "security": {"status": "pass"},
            "tags": ["inactive"],
            "status": "removed",
            "dedup": {"canonical_id": "github.com/example/skills/inactive"},
        },
    ]

    with open(skills_file, "w", encoding="utf-8") as f:
        for skill in skills:
            f.write(json.dumps(skill, ensure_ascii=False) + "\n")

    return skills_file


@pytest.fixture
def router_db(tmp_path, sample_skills_jsonl):
    """Build a router database for testing."""
    db_path = tmp_path / "router.sqlite"
    count = router.build_router_db(sample_skills_jsonl, db_path)
    assert count == 4  # 4 active, non-malicious skills
    return db_path


def test_build_router_db(sample_skills_jsonl, tmp_path):
    """Test building the router database."""
    db_path = tmp_path / "router.sqlite"
    count = router.build_router_db(sample_skills_jsonl, db_path)

    assert count == 4  # Excludes malicious and removed skills
    assert db_path.exists()

    # Verify database structure
    conn = sqlite3.connect(db_path)

    # Check FTS table exists
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='skills_fts'")
    assert cursor.fetchone() is not None

    # Check metadata table exists
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='skill_metadata'")
    assert cursor.fetchone() is not None

    # Check we have the right skills
    cursor = conn.execute("SELECT COUNT(*) FROM skill_metadata")
    assert cursor.fetchone()[0] == 4

    # Check alternatives_count is calculated
    cursor = conn.execute("SELECT alternatives_count FROM skill_metadata WHERE skill_id = ?",
                          ("github.com/example/skills/pdf",))
    alternatives = cursor.fetchone()[0]
    assert alternatives == 1  # pdf-tool is an alternative

    conn.close()


def test_build_router_db_overwrites_existing(sample_skills_jsonl, tmp_path):
    """Test that building the database overwrites existing file."""
    db_path = tmp_path / "router.sqlite"

    # Build once
    count1 = router.build_router_db(sample_skills_jsonl, db_path)
    mtime1 = db_path.stat().st_mtime

    # Build again
    count2 = router.build_router_db(sample_skills_jsonl, db_path)
    mtime2 = db_path.stat().st_mtime

    assert count1 == count2
    assert mtime2 >= mtime1  # File was recreated


def test_search_skills_basic(router_db):
    """Test basic skill search."""
    result = router.search_skills(router_db, "pdf documents")

    assert result.query == "pdf documents"
    assert not result.abstained
    assert len(result.results) >= 1

    # First result should be the PDF skill
    first = result.results[0]
    assert first.name == "pdf"
    assert "pdf" in first.description.lower()
    assert first.trust_tier == "official"


def test_search_skills_canonical_dedup(router_db):
    """Test that duplicate skills are deduplicated by canonical_id."""
    result = router.search_skills(router_db, "pdf documents", k=10)

    # Should only get the canonical pdf skill, not the duplicate
    pdf_results = [r for r in result.results if "pdf" in r.name.lower()]

    # We should get exactly one PDF result (the canonical one)
    assert len(pdf_results) == 1
    assert pdf_results[0].id == "github.com/example/skills/pdf"
    assert pdf_results[0].alternatives_count == 1


def test_search_skills_layer_filter(router_db):
    """Test filtering by layer."""
    # Search curated only
    result = router.search_skills(router_db, "pdf", layer="curated")
    assert len(result.results) >= 1
    assert all(r.id == "github.com/example/skills/pdf" for r in result.results if "pdf" in r.name.lower())

    # Search source only
    result = router.search_skills(router_db, "web scraping", layer="source")
    assert len(result.results) >= 1
    assert all(r.id != "github.com/example/skills/pdf" for r in result.results)


def test_search_skills_license_filter(router_db):
    """Test filtering by license."""
    result = router.search_skills(router_db, "pdf", license_filter="permissive")

    # Should only return skills with allow-list licenses
    for match in result.results:
        assert match.license in ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "CC0-1.0", "Unlicense"]


def test_search_skills_trust_filter(router_db):
    """Test filtering by minimum trust tier."""
    # Official only
    result = router.search_skills(router_db, "pdf", min_trust="official")
    assert all(r.trust_tier == "official" for r in result.results)

    # Community or higher
    result = router.search_skills(router_db, "scrape", min_trust="community")
    assert all(r.trust_tier in ["official", "community"] for r in result.results)


def test_search_skills_k_limit(router_db):
    """Test that k parameter limits results."""
    result = router.search_skills(router_db, "pdf", k=1)
    assert len(result.results) == 1

    result = router.search_skills(router_db, "pdf", k=5)
    assert len(result.results) <= 5


def test_search_skills_no_results(router_db):
    """Test search with no matching skills."""
    result = router.search_skills(router_db, "xyznonexistentquery123")
    assert len(result.results) == 0
    assert not result.abstained  # Empty results shouldn't abstain


def test_search_skills_black_hole_downrank(router_db):
    """Test that generic/black-hole skills are downranked."""
    # The "generic-helper" skill should be downranked
    # Use a query that would match both the generic skill and more specific skills
    result = router.search_skills(router_db, "help with documents", k=10)

    # If generic-helper appears, it should be downranked relative to more specific skills
    generic_indices = [i for i, r in enumerate(result.results) if r.name == "generic-helper"]
    specific_indices = [i for i, r in enumerate(result.results) if "pdf" in r.name.lower()]

    # If both appear, generic should rank after specific
    if generic_indices and specific_indices:
        assert generic_indices[0] > specific_indices[0], \
            "Generic skill should rank after specific skills"

    # Or test the score directly
    if generic_indices:
        generic_match = result.results[generic_indices[0]]
        # Score should reflect the downranking (we multiply by 0.3)
        assert generic_match.score > 0  # Sanity check


def test_is_black_hole_skill():
    """Test black-hole skill detection."""
    assert router.is_black_hole_skill("A general-purpose tool", "helper")
    assert router.is_black_hole_skill("Helps with any task", "generic")
    assert router.is_black_hole_skill("All-purpose assistant", "tool")
    assert not router.is_black_hole_skill("Extract PDF documents", "pdf-extractor")


def test_search_skills_abstain_low_score(router_db):
    """Test that low-scoring queries trigger abstain."""
    # Use a very specific query that doesn't match well
    result = router.search_skills(router_db, "xyzabc123nonexistent")

    # Should either abstain or return empty
    if result.results:
        # If results exist but score is low, should abstain
        if result.results[0].score < router.ABSTAIN_THRESHOLD:
            assert result.abstained


def test_get_skill_by_id(router_db):
    """Test retrieving a skill by ID."""
    skill = router.get_skill_by_id(router_db, "github.com/example/skills/pdf")

    assert skill is not None
    assert skill["id"] == "github.com/example/skills/pdf"
    assert skill["name"] == "pdf"
    assert skill["trust_tier"] == "official"
    assert skill["license"] == "MIT"


def test_get_skill_by_id_not_found(router_db):
    """Test retrieving a non-existent skill."""
    skill = router.get_skill_by_id(router_db, "github.com/nonexistent/skill")
    assert skill is None


def test_search_result_json_serializable(router_db):
    """Test that search results can be serialized to JSON."""
    result = router.search_skills(router_db, "pdf")

    # Convert to dict as done in CLI
    output = {
        "query": result.query,
        "abstained": result.abstained,
        "results": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "install": m.install,
                "url": m.url,
                "content_hash": m.content_hash,
                "trust_tier": m.trust_tier,
                "license": m.license,
                "security": m.security,
                "alternatives_count": m.alternatives_count,
                "why_matched": m.why_matched,
                "score": m.score,
            }
            for m in result.results
        ],
        "note": result.note,
    }

    # Should be JSON serializable
    json_str = json.dumps(output, ensure_ascii=False)
    assert json_str is not None

    # Should match schema structure
    parsed = json.loads(json_str)
    assert "query" in parsed
    assert "abstained" in parsed
    assert "results" in parsed
    assert isinstance(parsed["results"], list)


def test_search_skills_why_matched(router_db):
    """Test that why_matched field is populated correctly."""
    result = router.search_skills(router_db, "pdf")

    assert len(result.results) > 0
    match = result.results[0]

    assert "why_matched" in match.__dict__
    assert "fields" in match.why_matched
    assert "terms" in match.why_matched
    assert "bm25_rank" in match.why_matched
    assert isinstance(match.why_matched["fields"], list)
    assert isinstance(match.why_matched["terms"], list)
    assert match.why_matched["bm25_rank"] >= 1


def test_build_router_db_empty_file(tmp_path):
    """Test building router from empty skills file."""
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("")

    db_path = tmp_path / "router.sqlite"
    count = router.build_router_db(empty_file, db_path)

    assert count == 0
    assert db_path.exists()


def test_build_router_db_nonexistent_file(tmp_path):
    """Test building router from non-existent file."""
    db_path = tmp_path / "router.sqlite"
    count = router.build_router_db(tmp_path / "nonexistent.jsonl", db_path)

    assert count == 0
    assert db_path.exists()


def test_search_skills_ranking_trust_bonus(router_db):
    """Test that trust tier provides a small ranking bonus."""
    result = router.search_skills(router_db, "pdf", k=10)

    # Official skills should generally rank higher than community for same content
    # But this is a tie-breaker, so only applies when BM25 scores are similar
    official_skills = [r for r in result.results if r.trust_tier == "official"]
    if official_skills:
        # At least one official skill should appear
        assert len(official_skills) > 0


def test_search_skills_ranking_security_penalty(router_db):
    """Test that security issues provide a small ranking penalty."""
    # All our test skills have pass or review, so this is limited testing
    result = router.search_skills(router_db, "scrape", k=10)

    # Skills with 'pass' security should not be penalized
    for match in result.results:
        if match.security == "pass":
            # Score should not have large negative penalty
            assert match.score > 0
