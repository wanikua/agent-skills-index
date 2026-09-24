#!/usr/bin/env python3
"""Frontmatter parsing and validation for SKILL.md files.

Implements strict and lenient parsing modes according to PLAN §S1-4.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FrontmatterResult:
    """Result of frontmatter parsing."""

    raw: dict[str, Any]
    normalized: dict[str, Any]
    strict_valid: bool
    lenient_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dialects: list[str] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)


class FrontmatterParser:
    """Parser for SKILL.md frontmatter with strict and lenient modes."""

    # Strict name pattern: lowercase alphanumeric with hyphens
    NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

    # Known spec fields (SKILL.md v1 specification)
    SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

    # Dialect-specific extension keys
    DIALECT_MARKERS = {
        "claude-code": {"when_to_use", "disable-model-invocation"},
        "cursor": {"paths", "icon"},
        "codex": {"agents/openai.yaml"},  # File existence marker
    }

    def __init__(self, lenient: bool = False):
        """Initialize parser.

        Args:
            lenient: If True, apply lenient parsing rules
        """
        self.lenient = lenient

    def parse_file(self, path: Path, directory_name: str | None = None) -> FrontmatterResult:
        """Parse frontmatter from a SKILL.md file.

        Args:
            path: Path to SKILL.md file
            directory_name: Expected directory name for name validation (if None, extracts from path)

        Returns:
            FrontmatterResult with validation status and errors
        """
        if not path.exists():
            return FrontmatterResult(
                raw={},
                normalized={},
                strict_valid=False,
                lenient_valid=False,
                errors=[f"File not found: {path}"],
            )

        # Read file content
        try:
            content = path.read_bytes()
        except Exception as e:
            return FrontmatterResult(
                raw={},
                normalized={},
                strict_valid=False,
                lenient_valid=False,
                errors=[f"Failed to read file: {e}"],
            )

        # Remove BOM if present
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]

        # Decode as UTF-8
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            return FrontmatterResult(
                raw={},
                normalized={},
                strict_valid=False,
                lenient_valid=False,
                errors=[f"Invalid UTF-8 encoding: {e}"],
            )

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Extract frontmatter
        frontmatter_text, extract_error = self._extract_frontmatter(text)
        if extract_error:
            return FrontmatterResult(
                raw={},
                normalized={},
                strict_valid=False,
                lenient_valid=False,
                errors=[extract_error],
            )

        if not frontmatter_text:
            return FrontmatterResult(
                raw={},
                normalized={},
                strict_valid=False,
                lenient_valid=False,
                errors=["Missing frontmatter"],
            )

        # Parse YAML
        raw_data, parse_errors = self._parse_yaml(frontmatter_text)
        if parse_errors:
            return FrontmatterResult(
                raw=raw_data or {},
                normalized={},
                strict_valid=False,
                lenient_valid=False,
                errors=parse_errors,
            )

        # Determine directory name
        if directory_name is None:
            directory_name = path.parent.name if path.parent.name else "."

        # Validate
        return self._validate(raw_data, directory_name, path.parent)

    def _extract_frontmatter(self, text: str) -> tuple[str | None, str | None]:
        """Extract frontmatter from document text.

        Returns:
            (frontmatter_text, error_message)
        """
        lines = text.split("\n")

        # Find frontmatter delimiters
        if not lines or lines[0].strip() != "---":
            return None, "Frontmatter must start with '---'"

        # Find closing delimiter
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return None, "Frontmatter closing '---' not found"

        frontmatter_lines = lines[1:end_idx]
        return "\n".join(frontmatter_lines), None

    def _parse_yaml(self, yaml_text: str) -> tuple[dict[str, Any] | None, list[str]]:
        """Parse YAML text.

        Returns:
            (parsed_data, errors)
        """
        errors = []

        # Lenient mode: fix unquoted colons (Codex-style)
        if self.lenient:
            yaml_text = self._fix_unquoted_colons(yaml_text)

        try:
            data = yaml.safe_load(yaml_text)
        except yaml.YAMLError as e:
            errors.append(f"YAML parse error: {e}")
            return None, errors

        if not isinstance(data, dict):
            errors.append(f"Frontmatter must be a YAML mapping, got {type(data).__name__}")
            return None, errors

        return data, errors

    def _fix_unquoted_colons(self, yaml_text: str) -> str:
        """Fix unquoted colons in YAML values (lenient mode).

        Example: name: my:skill -> name: "my:skill"
        """
        lines = []
        for line in yaml_text.split("\n"):
            # Simple heuristic: if line has key: value with extra colons in value, quote it
            if ":" in line:
                match = re.match(r"^(\s*)([a-zA-Z_-]+):\s*(.+)$", line)
                if match and ":" in match.group(3):
                    indent, key, value = match.groups()
                    # Don't quote if already quoted or is a URL
                    if not (value.startswith('"') or value.startswith("'") or value.startswith("http")):
                        lines.append(f'{indent}{key}: "{value}"')
                        continue
            lines.append(line)
        return "\n".join(lines)

    def _validate(
        self, raw_data: dict[str, Any], directory_name: str, skill_dir: Path
    ) -> FrontmatterResult:
        """Validate frontmatter data in both strict and lenient modes.

        Args:
            raw_data: Parsed frontmatter data
            directory_name: Expected directory name
            skill_dir: Path to skill directory for dialect detection

        Returns:
            FrontmatterResult
        """
        result = FrontmatterResult(raw=raw_data, normalized={}, strict_valid=True, lenient_valid=True)

        # Check required fields
        if "name" not in raw_data:
            result.errors.append("Missing required field: name")
            result.strict_valid = False
            result.lenient_valid = False

        if "description" not in raw_data:
            result.errors.append("Missing required field: description")
            result.strict_valid = False
            result.lenient_valid = False

        # If missing required fields, stop here
        if not result.lenient_valid:
            return result

        # Validate name (strict)
        name = raw_data.get("name")
        if not isinstance(name, str):
            result.errors.append(f"name must be a string, got {type(name).__name__}")
            result.strict_valid = False
            result.lenient_valid = False
        else:
            # Check length
            if not (1 <= len(name) <= 64):
                result.errors.append(f"name length must be 1-64, got {len(name)}")
                result.strict_valid = False

            # Check pattern
            if not self.NAME_PATTERN.match(name):
                result.errors.append(f"name must match pattern ^[a-z0-9]+(-[a-z0-9]+)*$, got '{name}'")
                result.strict_valid = False

                # Check for non-ASCII separately
                if any(ord(c) > 127 for c in name):
                    result.errors.append("name-non-ascii")

            # Check directory name match
            if name != directory_name:
                result.errors.append(f"name '{name}' does not match directory name '{directory_name}'")
                result.strict_valid = False

        # Validate description
        description = raw_data.get("description")
        if not isinstance(description, str):
            result.errors.append(f"description must be a string, got {type(description).__name__}")
            result.strict_valid = False
            result.lenient_valid = False
        else:
            desc_len = len(description)
            if not (1 <= desc_len <= 1024):
                result.errors.append(f"description length must be 1-1024, got {desc_len}")
                result.strict_valid = False

        # Validate compatibility (optional)
        if "compatibility" in raw_data:
            compatibility = raw_data["compatibility"]
            if compatibility is not None:
                if not isinstance(compatibility, str):
                    result.errors.append(f"compatibility must be a string, got {type(compatibility).__name__}")
                    result.strict_valid = False
                elif len(compatibility) > 500:
                    result.errors.append(f"compatibility length must not exceed 500, got {len(compatibility)}")
                    result.strict_valid = False

        # Validate metadata (optional)
        if "metadata" in raw_data:
            metadata = raw_data["metadata"]
            if metadata is not None:
                if not isinstance(metadata, dict):
                    result.errors.append(f"metadata must be a mapping, got {type(metadata).__name__}")
                    result.strict_valid = False
                else:
                    # Check that all values are strings (strict)
                    for key, value in metadata.items():
                        if not isinstance(key, str):
                            result.errors.append(f"metadata key must be string, got {type(key).__name__}")
                            result.strict_valid = False
                            result.lenient_valid = False
                        if not isinstance(value, str):
                            # Non-string values always violate strict mode
                            result.strict_valid = False
                            if self.lenient:
                                # Coerce to string
                                result.warnings.append(
                                    f"metadata['{key}'] coerced from {type(value).__name__} to string"
                                )
                            else:
                                result.errors.append(
                                    f"metadata['{key}'] must be string, got {type(value).__name__}"
                                )
                                result.lenient_valid = False

        # Validate allowed-tools (optional)
        if "allowed-tools" in raw_data:
            allowed_tools = raw_data["allowed-tools"]
            if allowed_tools is not None and not isinstance(allowed_tools, str):
                result.errors.append(f"allowed-tools must be a string, got {type(allowed_tools).__name__}")
                result.strict_valid = False

        # Check for unknown top-level keys (strict)
        unknown_keys = set(raw_data.keys()) - self.SPEC_FIELDS
        if unknown_keys:
            # Unknown keys always violate strict mode
            result.strict_valid = False
            if self.lenient:
                # Move to extensions and infer dialects
                for key in unknown_keys:
                    result.extensions[key] = raw_data[key]
                result.dialects = self._infer_dialects(result.extensions, skill_dir)
                result.warnings.append(f"Unknown keys moved to extensions: {sorted(unknown_keys)}")
            else:
                result.errors.append(f"Unknown top-level keys: {sorted(unknown_keys)}")
                result.lenient_valid = False

        # Build normalized data
        metadata = (
            self._normalize_metadata(raw_data.get("metadata")) if self.lenient else raw_data.get("metadata")
        )
        result.normalized = {
            "name": raw_data.get("name"),
            "description": raw_data.get("description"),
            "license": raw_data.get("license"),
            "compatibility": raw_data.get("compatibility"),
            "metadata": metadata,
            "allowed-tools": raw_data.get("allowed-tools"),
            "extensions": result.extensions if self.lenient else {},
        }

        return result

    def _normalize_metadata(self, metadata: dict[str, Any] | None) -> dict[str, str] | None:
        """Normalize metadata values to strings (lenient mode)."""
        if metadata is None:
            return None
        if not isinstance(metadata, dict):
            return None

        normalized = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                normalized[key] = value
            else:
                # Coerce to string
                normalized[key] = str(value)
        return normalized

    def _infer_dialects(self, extensions: dict[str, Any], skill_dir: Path) -> list[str]:
        """Infer dialects from extension keys and directory contents."""
        dialects = []

        # Check extension keys
        for dialect, markers in self.DIALECT_MARKERS.items():
            if dialect == "codex":
                # Special case: check for file existence
                if (skill_dir / "agents" / "openai.yaml").exists():
                    dialects.append(dialect)
            else:
                # Check if any marker key is present
                if any(marker in extensions for marker in markers):
                    dialects.append(dialect)

        return sorted(dialects)


def lint_skill(skill_dir: Path, lenient: bool = False) -> FrontmatterResult:
    """Lint a skill directory.

    Args:
        skill_dir: Path to skill directory containing SKILL.md
        lenient: If True, use lenient parsing mode

    Returns:
        FrontmatterResult
    """
    skill_md = skill_dir / "SKILL.md"

    # Also check for lowercase variant
    if not skill_md.exists():
        skill_md_lower = skill_dir / "skill.md"
        if skill_md_lower.exists():
            result = FrontmatterParser(lenient=lenient).parse_file(
                skill_md_lower, directory_name=skill_dir.name
            )
            result.errors.insert(0, "filename-lowercase")
            result.strict_valid = False
            return result

    parser = FrontmatterParser(lenient=lenient)
    return parser.parse_file(skill_md, directory_name=skill_dir.name)
