#!/usr/bin/env python3
"""Quality linting for SKILL.md files.

Implements static quality checks according to PLAN §S2-6.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class QualityResult:
    """Result of quality linting."""

    smells: list[str] = field(default_factory=list)
    """List of detected quality smells."""


# Reserved words that should not be used as skill names
RESERVED_WORDS = {"anthropic", "claude"}

# Pattern to detect "when to use" signals in multiple languages
# Requires more context than just "when" alone
WHEN_TO_USE_PATTERN = re.compile(
    r"(\buse\s+(?:this\s+)?(?:skill\s+)?when\b|\buse\s+(?:this\s+)?for\b|\bwhen\s+(?:you\s+)?(?:need|want|should)\b|用于|当.*时)",
    re.IGNORECASE,
)

# Pattern to detect XML/HTML tags in description (requires closing tag or self-closing)
XML_TAG_PATTERN = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)[^>]*>|</[a-zA-Z][a-zA-Z0-9]*>")

# Pattern to detect backslash paths (Windows-style)
BACKSLASH_PATH_PATTERN = re.compile(r"[A-Za-z]:\\|\\[A-Za-z_]")


def count_words(text: str) -> int:
    """
    Count words in text.

    Uses a simple whitespace-based approach.
    For CJK languages, counts characters instead of words.

    Args:
        text: Text to count words in

    Returns:
        Word count
    """
    # Simple whitespace-based word count
    # For CJK, each character is roughly equivalent to a word
    words = text.split()
    return len(words)


def count_lines(content: str) -> int:
    """
    Count lines in content.

    Args:
        content: Content to count lines in

    Returns:
        Line count
    """
    if not content:
        return 0
    return len(content.splitlines())


def detect_xml_tags(text: str) -> bool:
    """
    Detect XML/HTML tags in text.

    Args:
        text: Text to check

    Returns:
        True if XML tags are present
    """
    return bool(XML_TAG_PATTERN.search(text))


def detect_backslash_paths(text: str) -> bool:
    """
    Detect backslash (Windows-style) paths.

    Args:
        text: Text to check

    Returns:
        True if backslash paths are present
    """
    return bool(BACKSLASH_PATH_PATTERN.search(text))


def detect_when_to_use_signal(text: str) -> bool:
    """
    Detect "when to use" signal in text.

    Looks for phrases like "when", "use when", "use for", "用于", "当...时", etc.

    Args:
        text: Text to check

    Returns:
        True if "when to use" signal is present
    """
    return bool(WHEN_TO_USE_PATTERN.search(text))


def lint_quality(
    skill_md_path: Path | None = None,
    content: str | None = None,
    name: str | None = None,
    description: str | None = None,
) -> QualityResult:
    """
    Perform quality linting on a skill.

    Can be called with either:
    - skill_md_path: Path to SKILL.md file
    - content + name + description: In-memory content

    Args:
        skill_md_path: Path to SKILL.md file (if available)
        content: SKILL.md content (if not reading from file)
        name: Skill name (if content is provided)
        description: Skill description (if content is provided)

    Returns:
        QualityResult with detected smells
    """
    result = QualityResult()

    # Read content if path provided
    if skill_md_path:
        if not skill_md_path.exists():
            return result
        try:
            content = skill_md_path.read_text(encoding="utf-8")
        except Exception:
            return result

    if not content:
        return result

    # Count words in body
    # Body is everything after frontmatter
    body_content = content
    if content.startswith("---\n"):
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            body_content = parts[1]

    word_count = count_words(body_content)
    if word_count > 5000:
        result.smells.append("body-too-long")

    # Count lines in entire file
    line_count = count_lines(content)
    if line_count > 500:
        result.smells.append("file-too-many-lines")

    # Check description length
    if description:
        desc_len = len(description)
        if desc_len > 1024:
            result.smells.append("description-too-long")
        elif desc_len < 40:
            result.smells.append("description-too-short")

        # Check for XML tags in description
        if detect_xml_tags(description):
            result.smells.append("description-has-xml-tags")

    # Check for backslash paths anywhere in content
    if detect_backslash_paths(content):
        result.smells.append("backslash-paths")

    # Check for "when to use" signal in entire content
    if not detect_when_to_use_signal(content):
        result.smells.append("missing-when-to-use")

    # Check reserved words in name
    if name and name.lower() in RESERVED_WORDS:
        result.smells.append("reserved-word-name")

    return result


def lint_quality_from_record(skill_record: dict[str, Any]) -> QualityResult:
    """
    Perform quality linting from a skill record (used during build).

    Args:
        skill_record: Skill record with name, description, and optionally content

    Returns:
        QualityResult with detected smells
    """
    return lint_quality(
        skill_md_path=None,
        content=skill_record.get("_raw_content"),  # Transient field during build
        name=skill_record.get("name"),
        description=skill_record.get("description"),
    )
