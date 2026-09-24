#!/usr/bin/env python3
"""Tests for frontmatter parsing and validation."""

from pathlib import Path

import pytest

from tools.atlas.frontmatter import FrontmatterParser, lint_skill

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "frontmatter"


class TestFrontmatterParser:
    """Test frontmatter parsing in strict and lenient modes."""

    def test_valid_basic_strict(self):
        """Test a valid basic skill passes strict mode."""
        result = lint_skill(FIXTURES_DIR / "valid-basic", lenient=False)
        assert result.strict_valid
        assert result.lenient_valid
        assert len(result.errors) == 0
        assert result.normalized["name"] == "valid-basic"

    def test_valid_basic_lenient(self):
        """Test a valid basic skill passes lenient mode."""
        result = lint_skill(FIXTURES_DIR / "valid-basic", lenient=True)
        assert result.strict_valid
        assert result.lenient_valid
        assert len(result.errors) == 0

    def test_with_bom(self):
        """Test that BOM is correctly handled."""
        result = lint_skill(FIXTURES_DIR / "with-bom", lenient=False)
        assert result.strict_valid
        assert result.lenient_valid
        assert result.normalized["name"] == "with-bom"

    def test_with_crlf(self):
        """Test that CRLF line endings are normalized."""
        result = lint_skill(FIXTURES_DIR / "with-crlf", lenient=False)
        assert result.strict_valid
        assert result.lenient_valid
        assert result.normalized["name"] == "with-crlf"

    def test_no_frontmatter(self):
        """Test that missing frontmatter is detected."""
        result = lint_skill(FIXTURES_DIR / "no-frontmatter", lenient=False)
        assert not result.strict_valid
        assert not result.lenient_valid
        assert any("frontmatter" in error.lower() for error in result.errors)

    def test_yaml_error(self):
        """Test that YAML errors are detected."""
        result = lint_skill(FIXTURES_DIR / "yaml-error", lenient=False)
        assert not result.strict_valid
        assert not result.lenient_valid
        assert any("yaml" in error.lower() for error in result.errors)

    def test_overlong_description(self):
        """Test that overlong descriptions fail strict mode."""
        result = lint_skill(FIXTURES_DIR / "overlong-description", lenient=False)
        assert not result.strict_valid
        assert any("description length" in error for error in result.errors)

    def test_name_mismatch(self):
        """Test that name must match directory name."""
        result = lint_skill(FIXTURES_DIR / "name-mismatch", lenient=False)
        assert not result.strict_valid
        assert any("does not match directory name" in error for error in result.errors)

    def test_toplevel_version_strict(self):
        """Test that top-level version fails in strict mode."""
        result = lint_skill(FIXTURES_DIR / "toplevel-version", lenient=False)
        assert not result.strict_valid
        assert any("unknown top-level keys" in error.lower() for error in result.errors)

    def test_toplevel_version_lenient(self):
        """Test that top-level version is moved to extensions in lenient mode."""
        result = lint_skill(FIXTURES_DIR / "toplevel-version", lenient=True)
        # Still strict_valid=False because of unknown keys
        assert not result.strict_valid
        # But lenient_valid=True because we handle it
        assert result.lenient_valid
        assert "version" in result.extensions
        assert result.extensions["version"] == "1.0.0"

    def test_vendor_extensions_strict(self):
        """Test that vendor extensions fail in strict mode."""
        result = lint_skill(FIXTURES_DIR / "vendor-extensions", lenient=False)
        assert not result.strict_valid
        assert any("unknown top-level keys" in error.lower() for error in result.errors)

    def test_vendor_extensions_lenient(self):
        """Test that vendor extensions are moved to extensions in lenient mode."""
        result = lint_skill(FIXTURES_DIR / "vendor-extensions", lenient=True)
        assert not result.strict_valid  # Extensions still violate strict
        assert result.lenient_valid
        assert "when_to_use" in result.extensions
        assert "icon" in result.extensions
        assert "paths" in result.extensions
        # Check dialect inference
        assert "claude-code" in result.dialects
        assert "cursor" in result.dialects

    def test_lowercase_filename(self):
        """Test that lowercase filename is detected."""
        result = lint_skill(FIXTURES_DIR / "lowercase-filename", lenient=False)
        assert not result.strict_valid
        assert "filename-lowercase" in result.errors

    def test_full_spec(self):
        """Test a skill with all spec fields."""
        result = lint_skill(FIXTURES_DIR / "full-spec", lenient=False)
        assert result.strict_valid
        assert result.lenient_valid
        assert result.normalized["name"] == "full-spec"
        assert result.normalized["compatibility"] is not None
        assert result.normalized["metadata"] is not None
        assert result.normalized["allowed-tools"] is not None

    def test_invalid_name_pattern(self):
        """Test that invalid name patterns are detected."""
        # Note: directory name is "invalid-name-pattern" but the name field is "Invalid_Name"
        result = lint_skill(FIXTURES_DIR / "invalid-name-pattern", lenient=False)
        assert not result.strict_valid
        # Should have both pattern error and mismatch error
        errors_text = " ".join(result.errors)
        assert "must match pattern" in errors_text

    def test_non_string_metadata_strict(self):
        """Test that non-string metadata fails in strict mode."""
        result = lint_skill(FIXTURES_DIR / "non-string-metadata", lenient=False)
        assert not result.strict_valid
        assert any("metadata" in error and "must be string" in error for error in result.errors)

    def test_non_string_metadata_lenient(self):
        """Test that non-string metadata is coerced in lenient mode."""
        result = lint_skill(FIXTURES_DIR / "non-string-metadata", lenient=True)
        assert not result.strict_valid  # Still fails strict
        assert result.lenient_valid  # But passes lenient
        assert result.normalized["metadata"]["version"] == "1.0"
        assert result.normalized["metadata"]["count"] == "42"
        assert result.normalized["metadata"]["enabled"] == "True"
        assert any("coerced" in warning for warning in result.warnings)

    def test_overlong_compatibility(self):
        """Test that overlong compatibility field fails strict mode."""
        result = lint_skill(FIXTURES_DIR / "overlong-compatibility", lenient=False)
        assert not result.strict_valid
        assert any("compatibility length" in error for error in result.errors)

    def test_name_non_ascii(self):
        """Test that non-ASCII names are flagged."""
        result = lint_skill(FIXTURES_DIR / "name-non-ascii", lenient=False)
        assert not result.strict_valid
        assert "name-non-ascii" in result.errors


class TestFrontmatterParserDirectParsing:
    """Test direct parsing with FrontmatterParser."""

    def test_strict_parser_rejects_extensions(self):
        """Test that strict parser rejects unknown keys."""
        parser = FrontmatterParser(lenient=False)
        skill_md = FIXTURES_DIR / "vendor-extensions" / "SKILL.md"
        result = parser.parse_file(skill_md, directory_name="vendor-extensions")
        assert not result.strict_valid
        assert "unknown top-level keys" in " ".join(result.errors).lower()

    def test_lenient_parser_accepts_extensions(self):
        """Test that lenient parser accepts unknown keys."""
        parser = FrontmatterParser(lenient=True)
        skill_md = FIXTURES_DIR / "vendor-extensions" / "SKILL.md"
        result = parser.parse_file(skill_md, directory_name="vendor-extensions")
        assert result.lenient_valid
        assert len(result.extensions) > 0

    def test_name_length_validation(self):
        """Test name length validation."""
        parser = FrontmatterParser(lenient=False)

        # Create a test with very long name
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skill_dir = tmppath / "test"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"

            # Name with 65 characters (exceeds max of 64)
            long_name = "a" * 65
            skill_md.write_text(
                f"---\nname: {long_name}\ndescription: Test\nlicense: MIT\n---\n\n# Test\n"
            )

            result = parser.parse_file(skill_md, directory_name="test")
            assert not result.strict_valid
            assert any("name length" in error for error in result.errors)

    def test_description_length_validation(self):
        """Test description length validation."""
        parser = FrontmatterParser(lenient=False)

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skill_dir = tmppath / "test"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"

            # Empty description
            skill_md.write_text("---\nname: test\ndescription: ''\nlicense: MIT\n---\n\n# Test\n")

            result = parser.parse_file(skill_md, directory_name="test")
            assert not result.strict_valid
            assert any("description length" in error for error in result.errors)

    def test_missing_required_fields(self):
        """Test that missing required fields are detected."""
        parser = FrontmatterParser(lenient=False)

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skill_dir = tmppath / "test"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"

            # Missing description
            skill_md.write_text("---\nname: test\nlicense: MIT\n---\n\n# Test\n")

            result = parser.parse_file(skill_md, directory_name="test")
            assert not result.strict_valid
            assert not result.lenient_valid
            assert any("description" in error for error in result.errors)


class TestDialectInference:
    """Test dialect inference from extension keys."""

    def test_claude_code_dialect(self):
        """Test inference of claude-code dialect."""
        parser = FrontmatterParser(lenient=True)

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skill_dir = tmppath / "test"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"

            skill_md.write_text(
                "---\nname: test\ndescription: Test\nlicense: MIT\nwhen_to_use: Always\n---\n\n# Test\n"
            )

            result = parser.parse_file(skill_md, directory_name="test")
            assert "claude-code" in result.dialects

    def test_cursor_dialect(self):
        """Test inference of cursor dialect."""
        parser = FrontmatterParser(lenient=True)

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skill_dir = tmppath / "test"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"

            skill_md.write_text(
                "---\nname: test\ndescription: Test\nlicense: MIT\nicon: 📄\n---\n\n# Test\n"
            )

            result = parser.parse_file(skill_md, directory_name="test")
            assert "cursor" in result.dialects

    def test_multiple_dialects(self):
        """Test that multiple dialects can be inferred."""
        result = lint_skill(FIXTURES_DIR / "vendor-extensions", lenient=True)
        # This fixture has both claude-code (when_to_use) and cursor (icon, paths) markers
        assert "claude-code" in result.dialects
        assert "cursor" in result.dialects


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
