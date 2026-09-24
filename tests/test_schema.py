"""Tests for schema validation (S1-1 acceptance criteria)."""

from pathlib import Path

import pytest

from tools.atlas.schema import SchemaValidator


@pytest.fixture
def validator():
    """Create a SchemaValidator instance."""
    return SchemaValidator()


@pytest.fixture
def valid_skill():
    """A valid skill record."""
    return {
        "id": "github.com/example/repo/skills/test",
        "name": "test-skill",
        "description": "A valid test skill for validation",
        "layer": "source",
        "source": {
            "host": "github.com",
            "repo": "example/repo",
            "path": "skills/test",
            "ref": "main",
            "commit": "a1b2c3d4e5f6789012345678901234567890abcd",
            "blob_sha": "b2c3d4e5f678901234567890abcd1234567890ab",
            "url": "https://github.com/example/repo/tree/a1b2c3d4/skills/test",
            "source_id": "example-repo",
        },
        "hashes": {
            "skill_md_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "content_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "folder_sha256": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        },
        "frontmatter": {
            "license": "MIT",
            "compatibility": None,
            "allowed_tools": None,
            "metadata": {},
            "extensions": {},
        },
        "conformance": {
            "strict": True,
            "lenient": True,
            "errors": [],
            "dialects": ["claude-code"],
        },
        "license": {
            "declared": "MIT",
            "spdx": "MIT",
            "evidence": "frontmatter",
            "file": None,
            "class": "allow",
        },
        "trust_tier": "official",
        "status": "active",
        "first_seen": "2026-09-24T00:00:00Z",
        "last_seen": "2026-09-24T08:00:00Z",
        "last_changed": "2026-09-24T08:00:00Z",
    }


@pytest.fixture
def valid_source():
    """A valid source record."""
    return {
        "id": "example-repo",
        "url": "https://github.com/example/repo",
        "owner_type": "vendor",
        "tier": 1,
        "status": "active",
        "added_at": "2026-09-24T00:00:00Z",
        "verified": True,
    }


@pytest.fixture
def valid_stats():
    """A valid stats record."""
    return {
        "schema_version": "2.0.0",
        "generated_at": "2026-09-24T08:00:00Z",
        "index_commit": "abc123",
        "total_skills": 42,
        "canonical_skills": 40,
        "repositories": 10,
        "curated_skills": 5,
    }


# Valid record tests


def test_valid_skill_passes(validator, valid_skill):
    """A valid skill record should pass validation."""
    errors = validator.validate_skill(valid_skill)
    assert errors == [], f"Valid skill should have no errors, got: {errors}"


def test_valid_source_passes(validator, valid_source):
    """A valid source record should pass validation."""
    errors = validator.validate_source(valid_source)
    assert errors == [], f"Valid source should have no errors, got: {errors}"


def test_valid_stats_passes(validator, valid_stats):
    """A valid stats record should pass validation."""
    errors = validator.validate_stats(valid_stats)
    assert errors == [], f"Valid stats should have no errors, got: {errors}"


# Invalid ID tests (S1-1 acceptance: "invalid id")


def test_skill_invalid_id_format(validator, valid_skill):
    """Skill with invalid ID format should fail validation."""
    valid_skill["id"] = "not-a-valid-id"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("id" in error.lower() for error in errors)


def test_skill_invalid_id_uppercase(validator, valid_skill):
    """Skill with uppercase in owner/repo should fail (IDs must be lowercase)."""
    valid_skill["id"] = "github.com/Example/Repo/skills/test"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("id" in error.lower() for error in errors)


def test_skill_missing_id(validator, valid_skill):
    """Skill without ID should fail validation."""
    del valid_skill["id"]
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("id" in error.lower() for error in errors)


# Missing hash field tests (S1-1 acceptance: "missing hash fields")


def test_skill_missing_all_hashes(validator, valid_skill):
    """Skill without hashes object should fail validation."""
    del valid_skill["hashes"]
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("hash" in error.lower() for error in errors)


def test_skill_missing_skill_md_sha256(validator, valid_skill):
    """Skill without skill_md_sha256 should fail validation."""
    del valid_skill["hashes"]["skill_md_sha256"]
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("skill_md_sha256" in error.lower() for error in errors)


def test_skill_missing_content_hash(validator, valid_skill):
    """Skill without content_hash should fail validation."""
    del valid_skill["hashes"]["content_hash"]
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("content_hash" in error.lower() for error in errors)


def test_skill_missing_folder_sha256(validator, valid_skill):
    """Skill without folder_sha256 should fail validation."""
    del valid_skill["hashes"]["folder_sha256"]
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("folder_sha256" in error.lower() for error in errors)


def test_skill_invalid_hash_format(validator, valid_skill):
    """Skill with incorrectly formatted hash should fail validation."""
    valid_skill["hashes"]["skill_md_sha256"] = "not-a-valid-hash"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("skill_md_sha256" in error.lower() for error in errors)


def test_skill_content_hash_missing_prefix(validator, valid_skill):
    """Skill with content_hash missing sha256: prefix should fail validation."""
    # Remove the sha256: prefix
    valid_skill["hashes"]["content_hash"] = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("content_hash" in error.lower() for error in errors)


# Additional invalid field tests


def test_skill_invalid_commit_sha(validator, valid_skill):
    """Skill with invalid commit SHA should fail validation."""
    valid_skill["source"]["commit"] = "not-40-chars"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("commit" in error.lower() for error in errors)


def test_skill_missing_required_field(validator, valid_skill):
    """Skill missing required field should fail validation."""
    del valid_skill["name"]
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("name" in error.lower() for error in errors)


def test_skill_invalid_layer(validator, valid_skill):
    """Skill with invalid layer value should fail validation."""
    valid_skill["layer"] = "invalid-layer"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("layer" in error.lower() for error in errors)


def test_skill_invalid_trust_tier(validator, valid_skill):
    """Skill with invalid trust tier should fail validation."""
    valid_skill["trust_tier"] = "invalid-tier"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("trust_tier" in error.lower() for error in errors)


def test_skill_invalid_status(validator, valid_skill):
    """Skill with invalid status should fail validation."""
    valid_skill["status"] = "invalid-status"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("status" in error.lower() for error in errors)


def test_skill_invalid_license_class(validator, valid_skill):
    """Skill with invalid license class should fail validation."""
    valid_skill["license"]["class"] = "invalid-class"
    errors = validator.validate_skill(valid_skill)
    assert len(errors) > 0
    assert any("class" in error.lower() for error in errors)


def test_source_missing_required_field(validator, valid_source):
    """Source missing required field should fail validation."""
    del valid_source["url"]
    errors = validator.validate_source(valid_source)
    assert len(errors) > 0
    assert any("url" in error.lower() for error in errors)


def test_source_invalid_tier(validator, valid_source):
    """Source with invalid tier should fail validation."""
    valid_source["tier"] = 99
    errors = validator.validate_source(valid_source)
    assert len(errors) > 0
    assert any("tier" in error.lower() for error in errors)


def test_stats_missing_required_field(validator, valid_stats):
    """Stats missing required field should fail validation."""
    del valid_stats["total_skills"]
    errors = validator.validate_stats(valid_stats)
    assert len(errors) > 0
    assert any("total_skills" in error.lower() for error in errors)


def test_stats_negative_count(validator, valid_stats):
    """Stats with negative count should fail validation."""
    valid_stats["total_skills"] = -1
    errors = validator.validate_stats(valid_stats)
    assert len(errors) > 0


# Wrapper file tests


def test_skills_json_wrapper_valid(validator, valid_skill):
    """Valid skills.json wrapper should pass validation."""
    wrapper = {
        "schema_version": "2.0.0",
        "generated_at": "2026-09-24T08:00:00Z",
        "description": "Test skills catalog",
        "total_count": 1,
        "curated_count": 0,
        "skills": [valid_skill],
    }
    errors = validator.validate_skills_json(wrapper)
    assert errors == [], f"Valid skills.json should have no errors, got: {errors}"


def test_skills_json_wrong_schema_version(validator):
    """skills.json with wrong schema version should fail."""
    wrapper = {
        "schema_version": "1.0.0",
        "skills": [],
    }
    errors = validator.validate_skills_json(wrapper)
    assert len(errors) > 0
    assert any("schema_version" in error.lower() for error in errors)


def test_sources_json_wrapper_valid(validator, valid_source):
    """Valid sources.json wrapper should pass validation."""
    wrapper = {
        "schema_version": "2.0.0",
        "generated_at": "2026-09-24T08:00:00Z",
        "description": "Test sources catalog",
        "total_repositories": 1,
        "repositories": [valid_source],
    }
    errors = validator.validate_sources_json(wrapper)
    assert errors == [], f"Valid sources.json should have no errors, got: {errors}"


def test_sources_json_wrong_schema_version(validator):
    """sources.json with wrong schema version should fail."""
    wrapper = {
        "schema_version": "1.0.0",
        "repositories": [],
    }
    errors = validator.validate_sources_json(wrapper)
    assert len(errors) > 0
    assert any("schema_version" in error.lower() for error in errors)


# Integration test with actual files


def test_actual_index_files_are_valid():
    """The actual index files in the repository should be valid."""
    from tools.atlas.schema import validate_index

    index_dir = Path(__file__).parent.parent / "index"
    all_valid, errors_by_file = validate_index(index_dir)

    if not all_valid:
        error_msg = "Index files have validation errors:\n"
        for filename, errors in errors_by_file.items():
            error_msg += f"\n{filename}:\n"
            for error in errors:
                error_msg += f"  - {error}\n"
        pytest.fail(error_msg)
