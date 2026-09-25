"""Tests for the atlas curate command."""

import json
import sys
from pathlib import Path

# Add tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.atlas.curate import (
    check_file_size,
    count_words,
    create_attribution,
    is_text_file,
    is_valid_for_curation,
    validate_skill_directory,
)


def test_count_words():
    """Test word counting."""
    assert count_words("hello world") == 2
    assert count_words("one two three four five") == 5
    assert count_words("") == 0
    # Note: split() removes leading/trailing spaces
    assert count_words("   spaces   between   ") == 2


def test_is_text_file():
    """Test text file extension validation."""
    assert is_text_file(Path("file.md"))
    assert is_text_file(Path("script.py"))
    assert is_text_file(Path("config.json"))
    assert is_text_file(Path("notes.txt"))
    assert is_text_file(Path("script.sh"))
    assert is_text_file(Path("code.js"))
    assert is_text_file(Path("code.ts"))
    assert is_text_file(Path("config.yaml"))
    assert is_text_file(Path("config.yml"))

    assert not is_text_file(Path("image.png"))
    assert not is_text_file(Path("data.bin"))
    assert not is_text_file(Path("doc.pdf"))
    assert not is_text_file(Path("archive.zip"))


def test_check_file_size(tmp_path):
    """Test file size checking."""
    # Create a small file
    small_file = tmp_path / "small.txt"
    small_file.write_text("Hello world")
    assert check_file_size(small_file)

    # Create a large file (> 1MB)
    large_file = tmp_path / "large.txt"
    large_file.write_bytes(b"x" * (1024 * 1024 + 1))
    assert not check_file_size(large_file)


def test_is_valid_for_curation_valid():
    """Test validation of a valid tier 1 skill."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "valid-tier1-allow.json") as f:
        skill = json.load(f)

    is_valid, reasons = is_valid_for_curation(skill)
    assert is_valid
    assert len(reasons) == 0


def test_is_valid_for_curation_deny_license():
    """Test that skills with deny license are rejected."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "invalid-license-deny.json") as f:
        skill = json.load(f)

    is_valid, reasons = is_valid_for_curation(skill)
    assert not is_valid
    assert any("license" in r.lower() for r in reasons)


def test_is_valid_for_curation_not_strict():
    """Test that skills without strict conformance are rejected."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "invalid-not-strict.json") as f:
        skill = json.load(f)

    is_valid, reasons = is_valid_for_curation(skill)
    assert not is_valid
    assert any("strict" in r.lower() for r in reasons)


def test_is_valid_for_curation_duplicate():
    """Test that duplicate skills are rejected."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "invalid-duplicate.json") as f:
        skill = json.load(f)

    is_valid, reasons = is_valid_for_curation(skill)
    assert not is_valid
    assert any("duplicate" in r.lower() for r in reasons)


def test_validate_skill_directory_valid():
    """Test validation of a valid skill directory."""
    skill_dir = Path(__file__).parent / "fixtures" / "skill-dirs" / "valid-skill"
    is_valid, violations = validate_skill_directory(skill_dir)
    assert is_valid
    assert len(violations) == 0


def test_validate_skill_directory_too_many_words():
    """Test that skills with too many words are rejected."""
    skill_dir = Path(__file__).parent / "fixtures" / "skill-dirs" / "too-many-words"
    is_valid, violations = validate_skill_directory(skill_dir)
    assert not is_valid
    assert any("word" in v.lower() for v in violations)


def test_validate_skill_directory_non_text_file():
    """Test that skills with non-text files are rejected."""
    skill_dir = Path(__file__).parent / "fixtures" / "skill-dirs" / "non-text-file"
    is_valid, violations = validate_skill_directory(skill_dir)
    assert not is_valid
    assert any("not a text file" in v.lower() for v in violations)


def test_validate_skill_directory_too_large_file():
    """Test that skills with files > 1MB are rejected."""
    skill_dir = Path(__file__).parent / "fixtures" / "skill-dirs" / "too-large-file"
    is_valid, violations = validate_skill_directory(skill_dir)
    assert not is_valid
    assert any("mb" in v.lower() for v in violations)


def test_create_attribution():
    """Test ATTRIBUTION.md generation."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "valid-tier1-allow.json") as f:
        skill = json.load(f)

    attribution = create_attribution(skill, modifications="none")

    # Check that key information is present
    assert "example-org/example-repo" in attribution
    assert "skills/valid-skill" in attribution
    assert "abc123" in attribution
    assert "MIT" in attribution
    # Check for Modifications field (with markdown bold formatting)
    assert "**Modifications:**" in attribution
    assert "none" in attribution


def test_curate_command_help():
    """Test that curate command is available."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "tools.atlas", "curate", "--help"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert "curate" in result.stdout.lower()
    assert "--id" in result.stdout
    assert "--auto-tier1" in result.stdout
    assert "--dry-run" in result.stdout


def test_curate_command_no_args():
    """Test that curate command requires arguments."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "tools.atlas", "curate"],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 1
    assert "must specify" in result.stdout.lower() or "must specify" in result.stderr.lower()


def test_curate_command_auto_tier1_empty_index():
    """Test auto-tier1 with empty index."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "tools.atlas", "curate", "--auto-tier1", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=Path(__file__).parent.parent,
    )
    # Should succeed but find no skills
    assert result.returncode == 0
    assert "no skills" in result.stdout.lower() or "found" in result.stdout.lower()


def test_is_valid_for_curation_security_pass():
    """Test that skills with security.status == pass are accepted."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "valid-with-security-pass.json") as f:
        skill = json.load(f)

    is_valid, reasons = is_valid_for_curation(skill)
    assert is_valid
    assert len(reasons) == 0


def test_is_valid_for_curation_security_warn():
    """Test that skills with security.status != pass are rejected."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"
    with open(fixtures_dir / "invalid-security-warn.json") as f:
        skill = json.load(f)

    is_valid, reasons = is_valid_for_curation(skill)
    assert not is_valid
    assert any("security" in r.lower() for r in reasons)
