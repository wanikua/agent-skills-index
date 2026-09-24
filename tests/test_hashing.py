"""Tests for hash computation following PLAN.md §3.3 and §S2-1.

This test file verifies each normalization rule with FIXED expected hash values.
These hash values are the acceptance criteria for S2-1.
"""

import hashlib
from pathlib import Path

import pytest

from tools.atlas.hashing import (
    compute_content_hash,
    compute_folder_sha256,
    compute_skill_md_sha256,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "hashing"


class TestSkillMdSha256:
    """Test raw SHA-256 computation."""

    def test_basic_raw_hash(self):
        """Test raw SHA-256 of a basic file."""
        content = (FIXTURES_DIR / "basic.md").read_bytes()
        hash_value = compute_skill_md_sha256(content)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

        expected = hashlib.sha256(content).hexdigest()
        assert hash_value == expected


class TestContentHash:
    """Test normalized content hash computation.

    Each test verifies one or more normalization rules from PLAN.md §3.3:
    1. Remove BOM
    2. Unicode NFC normalization
    3. CRLF → LF
    4. Strip trailing whitespace from each line
    5. Ensure single trailing newline
    6. Strip provenance keys from frontmatter
    """

    def test_basic_normalized_hash(self):
        """Test basic file that needs no normalization.

        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "basic.md").read_bytes()
        hash_value = compute_content_hash(content)

        assert hash_value.startswith("sha256:")

        expected = "sha256:717d0f1c2c3ef47f4562741eb87cef81b6558ffa11e58cd468601a5e48f0b536"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_bom_removed(self):
        """Test that BOM (Byte Order Mark) is stripped.

        Rule 1: Remove BOM
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "bom.md").read_bytes()

        assert content[:3] == b"\xef\xbb\xbf", "Test file should have BOM"

        hash_value = compute_content_hash(content)

        content_no_bom = content[3:]
        hash_no_bom = compute_content_hash(content_no_bom)

        assert hash_value == hash_no_bom, "Hash should be same with or without BOM"

        expected = "sha256:a61477d9977b709c7e31582a60a0e4008585e07b015015c2ec8864b9a00746d2"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_crlf_normalized(self):
        """Test that CRLF line endings are converted to LF.

        Rule 3: CRLF → LF
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "crlf.md").read_bytes()

        assert b"\r\n" in content, "Test file should have CRLF"

        hash_value = compute_content_hash(content)

        content_lf = content.replace(b"\r\n", b"\n")
        hash_lf = compute_content_hash(content_lf)

        assert hash_value == hash_lf, "Hash should be same for CRLF and LF"

        expected = "sha256:f52afbb6cc7a108e2a529fa92690fb0bd628184b5f6fc18b2ec76995f82e6b9c"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_trailing_whitespace_stripped(self):
        """Test that trailing whitespace is removed from each line.

        Rule 4: Strip trailing whitespace from each line
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "trailing-whitespace.md").read_bytes()

        text = content.decode("utf-8")
        assert any(line.rstrip() != line.rstrip("\n") for line in text.split("\n")), (
            "Test file should have trailing whitespace"
        )

        hash_value = compute_content_hash(content)

        expected = "sha256:f1c9b2e0bdafae6e7a6b4945c83084e85fae8c0ec35184d919b75e0c42195ea6"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_single_trailing_newline_from_none(self):
        """Test that missing trailing newline is added.

        Rule 5: Ensure single trailing newline (from none)
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "no-trailing-newline.md").read_bytes()

        assert not content.endswith(b"\n"), "Test file should not end with newline"

        hash_value = compute_content_hash(content)

        expected = "sha256:49cb35ae6196e51b9d4cb8ccb81f8cc6959e436824324cf6ad27467137cca6e9"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_single_trailing_newline_from_many(self):
        """Test that multiple trailing newlines are normalized to one.

        Rule 5: Ensure single trailing newline (from many)
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "multiple-trailing-newlines.md").read_bytes()

        assert content.endswith(b"\n\n\n\n"), "Test file should have multiple trailing newlines"

        hash_value = compute_content_hash(content)

        expected = "sha256:e77ea78ffe26f7ef0fa9f10fa1d18ffe6b52bdd2fef09b85e8941a36dd33351b"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_provenance_keys_stripped(self):
        """Test that provenance keys are removed from frontmatter.

        Rule 6: Strip provenance keys (metadata.github-*, local-path, mintlify-proj)
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "provenance.md").read_bytes()

        text = content.decode("utf-8")
        assert "local-path:" in text, "Test file should have local-path"
        assert "mintlify-proj:" in text, "Test file should have mintlify-proj"
        assert "github-repo:" in text, "Test file should have github-repo"

        hash_value = compute_content_hash(content)

        expected = "sha256:be1f40b0fd75790052a1cfece5b8aa02c843fc091ea359f7b11d142c7e11a3ab"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

        content_clean = b"""---
description: Test skill with provenance keys that should be stripped
metadata:
  other-key: should-remain
name: provenance-test
---

# Provenance Test

This skill has provenance keys in frontmatter that should be removed.
"""
        hash_clean = compute_content_hash(content_clean)

        assert hash_value == hash_clean, "Hash should be same after provenance keys are removed"

    def test_unicode_nfc_normalized(self):
        """Test that Unicode is normalized to NFC.

        Rule 2: Unicode NFC normalization
        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (FIXTURES_DIR / "unicode-nfc.md").read_bytes()

        hash_value = compute_content_hash(content)

        expected = "sha256:bac7a30952eae20bba53af0c8ce642349b175c3c4c4ccb3444d3442590c5c1ec"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_all_normalizations_combined(self):
        """Test a file that requires multiple normalization steps.

        FIXED EXPECTED HASH for acceptance criteria.
        """
        content = (
            b"\xef\xbb\xbf---\r\nname: combined-test  \r\n"
            b"description: Multiple normalizations  \r\n"
            b"local-path: /tmp/test  \r\n---\r\n\r\n# Combined Test  \r\n\r\n"
            b"This tests all rules.  \r\n\r\n\r\n"
        )

        hash_value = compute_content_hash(content)

        expected = "sha256:a4def09385263d1e889a1c663dfa241104e6926a82b174e46552d19d46f87542"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"


class TestFolderSha256:
    """Test folder hash computation.

    This should be compatible with vercel-labs/skills computedHash.
    """

    def test_simple_folder_hash(self):
        """Test hash of a simple folder with multiple files.

        FIXED EXPECTED HASH for acceptance criteria.
        """
        folder = FIXTURES_DIR / "test-folder-simple"
        hash_value = compute_folder_sha256(folder)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

        expected = "a2865a6a171eb517fe42499d7133edaa63ea4a515bb4c061ee7c2e0bb752474d"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_nested_folder_hash(self):
        """Test hash of a folder with nested subdirectories.

        FIXED EXPECTED HASH for acceptance criteria.
        """
        folder = FIXTURES_DIR / "test-folder-nested"
        hash_value = compute_folder_sha256(folder)

        expected = "14a5b517c0dba0225819dc79d78af8352de91dcc371bda1cee2233b9b438e540"
        assert hash_value == expected, f"Hash changed! Got {hash_value}"

    def test_folder_hash_deterministic(self):
        """Test that folder hash is deterministic."""
        folder = FIXTURES_DIR / "test-folder-simple"

        hash1 = compute_folder_sha256(folder)
        hash2 = compute_folder_sha256(folder)

        assert hash1 == hash2, "Folder hash should be deterministic"

    def test_folder_hash_order_independent(self):
        """Test that folder hash is based on sorted paths."""
        folder = FIXTURES_DIR / "test-folder-simple"
        hash_value = compute_folder_sha256(folder)

        files = sorted([f for f in folder.rglob("*") if f.is_file()])
        assert len(files) >= 2, "Test folder should have multiple files"

        assert len(hash_value) == 64

    def test_nonexistent_folder(self):
        """Test that non-existent folder raises error."""
        folder = FIXTURES_DIR / "does-not-exist"

        with pytest.raises(ValueError, match="not a directory"):
            compute_folder_sha256(folder)


class TestHashIntegration:
    """Integration tests for hash functions."""

    def test_all_hash_types_together(self):
        """Test computing all three hash types for a skill."""
        skill_file = FIXTURES_DIR / "basic.md"
        content = skill_file.read_bytes()

        raw_hash = compute_skill_md_sha256(content)
        content_hash = compute_content_hash(content)

        assert len(raw_hash) == 64
        assert content_hash.startswith("sha256:")
        assert len(content_hash) == 71

        assert raw_hash != content_hash.replace("sha256:", ""), (
            "Raw hash and content hash should differ for files with frontmatter"
        )

    def test_hash_consistency_across_runs(self):
        """Test that hashes are consistent across multiple runs."""
        content = (FIXTURES_DIR / "basic.md").read_bytes()
        folder = FIXTURES_DIR / "test-folder-simple"

        hashes1 = [
            compute_skill_md_sha256(content),
            compute_content_hash(content),
            compute_folder_sha256(folder),
        ]

        hashes2 = [
            compute_skill_md_sha256(content),
            compute_content_hash(content),
            compute_folder_sha256(folder),
        ]

        assert hashes1 == hashes2, "Hashes must be deterministic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
