#!/usr/bin/env python3
"""Tests for gate integration (S2-7)."""

import json

from tools.atlas.gate import BLOCKING_SMELLS, gate_curated, gate_source


def test_gate_source_pass():
    """Test source gate with a valid skill."""
    skill = {
        "id": "github.com/example/repo/skill-test",
        "name": "test-skill",
        "description": "A test skill for source gate validation",
        "status": "active",
        "security": {"status": "pass"},
        "hashes": {
            "skill_md_sha256": "abc123",
            "content_hash": "sha256:def456",
            "folder_sha256": "ghi789",
        },
        "source": {
            "commit": "1234567890abcdef1234567890abcdef12345678",
        },
    }

    result = gate_source(skill)
    assert result.passes
    assert len(result.reasons) == 0
    assert result.gate_type == "source"


def test_gate_source_fail_missing_fields():
    """Test source gate fails when required fields missing."""
    skill = {
        "id": "github.com/example/repo/skill-test",
        # Missing name and description
        "status": "active",
        "security": {"status": "pass"},
        "hashes": {
            "skill_md_sha256": "abc123",
            # Missing content_hash
            "folder_sha256": "ghi789",
        },
        "source": {},  # Missing commit
    }

    result = gate_source(skill)
    assert not result.passes
    assert "Missing required field: name" in result.reasons
    assert "Missing required field: description" in result.reasons
    assert "Missing required hash: content_hash" in result.reasons
    assert "Missing source commit SHA" in result.reasons


def test_gate_source_fail_malicious():
    """Test source gate fails for malicious skills."""
    skill = {
        "id": "github.com/example/repo/malicious",
        "name": "malicious",
        "description": "A malicious skill",
        "status": "active",
        "security": {"status": "malicious"},
        "hashes": {
            "skill_md_sha256": "abc123",
            "content_hash": "sha256:def456",
            "folder_sha256": "ghi789",
        },
        "source": {"commit": "1234567890abcdef1234567890abcdef12345678"},
    }

    result = gate_source(skill)
    assert not result.passes
    assert "Security status is 'malicious'" in result.reasons


def test_gate_source_fail_dangling():
    """Test source gate fails for dangling skills."""
    skill = {
        "id": "github.com/deleted/repo/skill",
        "name": "deleted-skill",
        "description": "A skill from deleted repo",
        "status": "dangling",
        "security": {"status": "pass"},
        "hashes": {
            "skill_md_sha256": "abc123",
            "content_hash": "sha256:def456",
            "folder_sha256": "ghi789",
        },
        "source": {"commit": "1234567890abcdef1234567890abcdef12345678"},
    }

    result = gate_source(skill)
    assert not result.passes
    assert any("dangling" in reason.lower() for reason in result.reasons)


def test_gate_curated_minimal_pass_with_missing_license():
    """Test curated gate with minimal passing skill (will fail on LICENSE check)."""
    skill = {
        "id": "github.com/example/repo/skill-curated",
        "name": "curated-skill",
        "description": "A properly curated skill for testing curated gate validation requirements",
        "layer": "curated",
        "status": "active",
        "trust_tier": "official",
        "curated_path": "curated/example/repo/skill-curated",
        "conformance": {
            "strict": True,
            "lenient": True,
            "errors": [],
        },
        "license": {
            "class": "allow",
            "spdx": "MIT",
        },
        "security": {
            "status": "pass",
            "scans": [
                {"engine": "ioc_scanner", "ioc_patterns": []},
            ],
            "external_refs": [],
        },
        "quality": {
            "smells": [],
        },
    }

    result = gate_curated(skill)
    # Will fail because LICENSE file doesn't exist (expected in unit test)
    assert not result.passes
    assert "Missing LICENSE file in curated directory" in result.reasons


def test_gate_curated_fail_filename_lowercase():
    """Test curated gate fails for lowercase filename."""
    skill = {
        "id": "github.com/example/repo/bad-case",
        "name": "bad-case",
        "description": "A skill with lowercase SKILL.md filename (should fail curated gate check)",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/bad-case",
        "conformance": {
            "strict": False,
            "lenient": True,
            "errors": ["filename-lowercase"],
        },
        "license": {"class": "allow"},
        "security": {"status": "pass", "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}], "external_refs": []},
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert "SKILL.md filename must be exact case (not skill.md)" in result.reasons


def test_gate_curated_fail_license_deny():
    """Test curated gate fails for deny license class."""
    skill = {
        "id": "github.com/example/repo/gpl-skill",
        "name": "gpl-skill",
        "description": "A skill with GPL license that should not be curated due to license restrictions",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/gpl-skill",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "deny", "spdx": "GPL-3.0"},
        "security": {"status": "pass", "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}], "external_refs": []},
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert any("license class" in reason.lower() for reason in result.reasons)


def test_gate_curated_fail_security_malicious():
    """Test curated gate fails for malicious skills."""
    skill = {
        "id": "github.com/example/repo/malicious-curated",
        "name": "malicious",
        "description": "A malicious skill that somehow got into curated layer (gate should catch this)",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/malicious",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {
            "status": "malicious",
            "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}],
            "external_refs": [],
        },
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert "Security status is 'malicious'" in result.reasons


def test_gate_curated_fail_high_severity():
    """Test curated gate fails for unresolved HIGH severity findings."""
    skill = {
        "id": "github.com/example/repo/high-severity",
        "name": "high-risk",
        "description": "A skill with high severity security findings that must be resolved before curation",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/high-risk",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {
            "status": "review",
            "scans": [
                {
                    "engine": "ioc_scanner",
                    "ioc_patterns": [
                        {"name": "eval_exec", "severity": "high"},
                    ],
                }
            ],
            "external_refs": [],
        },
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    # Should have reason about HIGH finding
    assert any("HIGH" in reason for reason in result.reasons)


def test_gate_curated_fail_blocking_smells():
    """Test curated gate fails for blocking quality smells."""
    for smell in BLOCKING_SMELLS:
        skill = {
            "id": f"github.com/example/repo/{smell}",
            "name": "smell-test",
            "description": "Skill with blocking quality smell that prevents curation approval process",
            "layer": "curated",
            "status": "active",
            "trust_tier": "community",
            "curated_path": f"curated/example/repo/{smell}",
            "conformance": {"strict": True, "lenient": True, "errors": []},
            "license": {"class": "allow"},
            "security": {
                "status": "pass",
                "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}],
                "external_refs": [],
            },
            "quality": {"smells": [smell]},
        }

        result = gate_curated(skill)
        assert not result.passes
        assert f"Blocking quality smell: {smell}" in result.reasons


def test_gate_curated_fail_aggregator_copy():
    """Test curated gate fails for aggregator copies."""
    skill = {
        "id": "github.com/copypasta/skills/stolen-skill",
        "name": "stolen",
        "description": "A skill copied from another repo without proper attribution or upstream linking",
        "layer": "curated",
        "status": "active",
        "trust_tier": "aggregator-copy",
        "curated_path": "curated/copypasta/skills/stolen",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {"status": "pass", "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}], "external_refs": []},
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert any("aggregator" in reason.lower() for reason in result.reasons)


def test_gate_curated_fail_not_curated_layer():
    """Test curated gate fails if layer is not 'curated'."""
    skill = {
        "id": "github.com/example/repo/source-only",
        "name": "source-skill",
        "description": "A skill that is only in source layer and not properly curated yet for production",
        "layer": "source",  # Not curated!
        "status": "active",
        "trust_tier": "community",
        "curated_path": None,
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {"status": "pass", "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}], "external_refs": []},
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert any("layer" in reason.lower() and "not" in reason.lower() for reason in result.reasons)


def test_gate_curated_no_ioc_scanner():
    """Test curated gate requires at least IOC scanner."""
    skill = {
        "id": "github.com/example/repo/no-scan",
        "name": "no-scan",
        "description": "A skill with no security scans at all which should fail curated gate validation",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/no-scan",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {"status": "pass", "scans": [], "external_refs": []},
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert "Missing IOC scanner (required)" in result.reasons


def test_gate_curated_only_ioc_scanner_passes():
    """Test curated gate accepts IOC scanner only (external scanners are best-effort)."""
    skill = {
        "id": "github.com/example/repo/ioc-only",
        "name": "ioc-only",
        "description": "A skill with only IOC scanner (external scanners unavailable but best-effort)",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/ioc-only",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {
            "status": "pass",
            "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}],
            "external_refs": [],
        },
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    # Should fail only on LICENSE file (not on scanner count)
    assert not result.passes
    assert "Missing LICENSE file in curated directory" in result.reasons
    # Should NOT fail on dual-engine requirement
    assert not any("dual-engine" in reason.lower() for reason in result.reasons)


def test_gate_result_to_dict():
    """Test GateResult.to_dict() serialization."""
    skill = {
        "id": "github.com/test/repo/skill",
        "name": "test",
        "description": "Test skill for JSON serialization of gate results and structured output validation",
        "status": "active",
        "security": {"status": "pass"},
        "hashes": {
            "skill_md_sha256": "abc",
            "content_hash": "sha256:def",
            "folder_sha256": "ghi",
        },
        "source": {"commit": "1234567890abcdef1234567890abcdef12345678"},
    }

    result = gate_source(skill)
    data = result.to_dict()

    assert data["skill_id"] == skill["id"]
    assert data["gate"] == "source"
    assert data["passes"] is True
    assert isinstance(data["reasons"], list)

    # Ensure it's JSON serializable
    json.dumps(data)


def test_gate_curated_with_critical_dangling_ref():
    """Test curated gate fails for critical dangling external refs."""
    skill = {
        "id": "github.com/example/repo/dangling-ref",
        "name": "dangling-ref",
        "description": "A skill with critical dangling external reference that breaks functionality",
        "layer": "curated",
        "status": "active",
        "trust_tier": "community",
        "curated_path": "curated/example/repo/dangling-ref",
        "conformance": {"strict": True, "lenient": True, "errors": []},
        "license": {"class": "allow"},
        "security": {
            "status": "pass",
            "scans": [{"engine": "ioc_scanner", "ioc_patterns": []}],
            "external_refs": [
                {"reference": "github.com/missing/repo", "exists": False, "critical": True},
            ],
        },
        "quality": {"smells": []},
    }

    result = gate_curated(skill)
    assert not result.passes
    assert any("Critical external reference is dangling" in reason for reason in result.reasons)
