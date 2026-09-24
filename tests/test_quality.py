#!/usr/bin/env python3
"""Tests for quality linting."""

from pathlib import Path

from tools.atlas.quality import (
    count_lines,
    count_words,
    detect_backslash_paths,
    detect_when_to_use_signal,
    detect_xml_tags,
    lint_quality,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "quality"


def test_count_words():
    """Test word counting."""
    assert count_words("one two three") == 3
    assert count_words("one") == 1
    assert count_words("") == 0
    assert count_words("one  two   three") == 3  # Multiple spaces


def test_count_lines():
    """Test line counting."""
    assert count_lines("one\ntwo\nthree") == 3
    assert count_lines("one") == 1
    assert count_lines("") == 0  # Empty string has 0 lines


def test_detect_xml_tags():
    """Test XML tag detection."""
    assert detect_xml_tags("Hello <strong>world</strong>") is True
    assert detect_xml_tags("Hello <a href='#'>link</a>") is True
    assert detect_xml_tags("<p>Paragraph</p>") is True
    assert detect_xml_tags("Hello world") is False
    assert detect_xml_tags("Use angle brackets 1 < 2 but not tags") is False


def test_detect_backslash_paths():
    """Test backslash path detection."""
    assert detect_backslash_paths("C:\\Users\\Documents\\file.txt") is True
    assert detect_backslash_paths("\\Users\\profile") is True
    assert detect_backslash_paths("Path: D:\\data\\file.csv") is True
    assert detect_backslash_paths("/usr/local/bin") is False
    assert detect_backslash_paths("./relative/path") is False
    assert detect_backslash_paths("No paths here") is False


def test_detect_when_to_use_signal():
    """Test when-to-use signal detection."""
    # English variants
    assert detect_when_to_use_signal("Use this when you need to parse JSON") is True
    assert detect_when_to_use_signal("Use when processing CSV files") is True
    assert detect_when_to_use_signal("Use for image analysis tasks") is True
    assert detect_when_to_use_signal("Use this skill when working with PDFs") is True
    assert detect_when_to_use_signal("When you need to analyze data") is True

    # Chinese variants
    assert detect_when_to_use_signal("用于处理图像文件") is True
    assert detect_when_to_use_signal("当需要解析JSON时使用") is True

    # Missing signal
    assert detect_when_to_use_signal("This skill does something useful") is False
    assert detect_when_to_use_signal("Install and run the tool") is False


def test_body_too_long():
    """Test detection of excessively long body content."""
    skill_path = FIXTURES_DIR / "body-too-long" / "SKILL.md"
    result = lint_quality(skill_md_path=skill_path)
    assert "body-too-long" in result.smells


def test_file_too_many_lines():
    """Test detection of files with too many lines."""
    skill_path = FIXTURES_DIR / "file-too-many-lines" / "SKILL.md"
    result = lint_quality(skill_md_path=skill_path)
    assert "file-too-many-lines" in result.smells


def test_description_too_long():
    """Test detection of excessively long descriptions."""
    skill_path = FIXTURES_DIR / "description-too-long" / "SKILL.md"

    # Read the file to extract description
    content = skill_path.read_text()

    # Extract description from frontmatter
    lines = content.split("\n")
    description = None
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break
        elif in_frontmatter and line.startswith("description:"):
            description = line.split("description:", 1)[1].strip()

    result = lint_quality(content=content, description=description, name="description-too-long")
    assert "description-too-long" in result.smells


def test_description_too_short():
    """Test detection of too-short descriptions."""
    skill_path = FIXTURES_DIR / "description-too-short" / "SKILL.md"
    content = skill_path.read_text()

    result = lint_quality(content=content, description="Short desc", name="description-too-short")
    assert "description-too-short" in result.smells


def test_description_has_xml_tags():
    """Test detection of XML tags in descriptions."""
    skill_path = FIXTURES_DIR / "description-has-xml-tags" / "SKILL.md"
    content = skill_path.read_text()

    description = (
        "This description contains <strong>XML tags</strong> "
        "and <a href='#'>links</a> which should be detected"
    )
    result = lint_quality(content=content, description=description, name="description-has-xml-tags")
    assert "description-has-xml-tags" in result.smells


def test_backslash_paths():
    """Test detection of backslash paths in content."""
    skill_path = FIXTURES_DIR / "backslash-paths" / "SKILL.md"
    result = lint_quality(skill_md_path=skill_path)
    assert "backslash-paths" in result.smells


def test_missing_when_to_use():
    """Test detection of missing when-to-use signal."""
    skill_path = FIXTURES_DIR / "missing-when-to-use" / "SKILL.md"
    result = lint_quality(skill_md_path=skill_path)
    assert "missing-when-to-use" in result.smells


def test_reserved_word_name():
    """Test detection of reserved words as skill name."""
    skill_path = FIXTURES_DIR / "reserved-word-name" / "SKILL.md"
    result = lint_quality(skill_md_path=skill_path, name="anthropic")
    assert "reserved-word-name" in result.smells

    # Test the other reserved word
    result = lint_quality(content="---\nname: claude\n---\n\nUse when needed.", name="claude", description="Test")
    assert "reserved-word-name" in result.smells


def test_all_good():
    """Test that a well-formatted skill passes all checks."""
    skill_path = FIXTURES_DIR / "all-good" / "SKILL.md"
    content = skill_path.read_text()
    description = "A well-formatted skill that passes all quality checks and serves as a baseline for comparison"

    result = lint_quality(content=content, description=description, name="all-good")
    assert len(result.smells) == 0


def test_multiple_smells():
    """Test that multiple smells can be detected in one skill."""
    content = """---
name: anthropic
description: Short
---

No when to use signal here.

This also has backslash paths: C:\\Users\\test
"""

    result = lint_quality(content=content, name="anthropic", description="Short")

    # Should detect multiple issues
    assert "reserved-word-name" in result.smells
    assert "description-too-short" in result.smells
    assert "backslash-paths" in result.smells
    assert "missing-when-to-use" in result.smells
    assert len(result.smells) == 4


def test_empty_content():
    """Test handling of empty or missing content."""
    result = lint_quality(content=None)
    assert len(result.smells) == 0

    result = lint_quality(content="")
    # Empty content should not crash, but won't detect many issues
    assert isinstance(result.smells, list)


def test_nonexistent_file():
    """Test handling of nonexistent files."""
    result = lint_quality(skill_md_path=Path("/nonexistent/path/SKILL.md"))
    assert len(result.smells) == 0  # Should not crash, just return empty result
