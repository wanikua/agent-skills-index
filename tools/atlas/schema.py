#!/usr/bin/env python3
"""Schema validation for Skill Atlas index files."""

import json
from pathlib import Path
from typing import Any

from jsonschema.validators import Draft202012Validator


class SchemaValidator:
    """Validates Skill Atlas index files against JSON schemas."""

    def __init__(self, schema_dir: Path | None = None):
        """Initialize validator with schema directory."""
        if schema_dir is None:
            # Default to index/schema relative to this file
            schema_dir = Path(__file__).parent.parent.parent / "index" / "schema"
        self.schema_dir = schema_dir
        self._schemas: dict[str, dict[str, Any]] = {}

    def load_schema(self, name: str) -> dict[str, Any]:
        """Load a schema by name (e.g., 'skill', 'source', 'stats')."""
        if name not in self._schemas:
            schema_path = self.schema_dir / f"{name}.schema.json"
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema not found: {schema_path}")
            with open(schema_path, encoding="utf-8") as f:
                self._schemas[name] = json.load(f)
        return self._schemas[name]

    def validate_skill(self, skill: dict[str, Any]) -> list[str]:
        """Validate a skill record. Returns list of error messages (empty if valid)."""
        schema = self.load_schema("skill")
        validator = Draft202012Validator(schema)
        errors = []
        for error in validator.iter_errors(skill):
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{path}: {error.message}")
        return errors

    def validate_source(self, source: dict[str, Any]) -> list[str]:
        """Validate a source record. Returns list of error messages (empty if valid)."""
        schema = self.load_schema("source")
        validator = Draft202012Validator(schema)
        errors = []
        for error in validator.iter_errors(source):
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{path}: {error.message}")
        return errors

    def validate_stats(self, stats: dict[str, Any]) -> list[str]:
        """Validate stats record. Returns list of error messages (empty if valid)."""
        schema = self.load_schema("stats")
        validator = Draft202012Validator(schema)
        errors = []
        for error in validator.iter_errors(stats):
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{path}: {error.message}")
        return errors

    def validate_skills_json(self, data: dict[str, Any]) -> list[str]:
        """Validate skills.json wrapper file."""
        errors = []

        # Check schema_version
        if "schema_version" not in data:
            errors.append("Missing schema_version")
        elif data["schema_version"] != "2.0.0":
            errors.append(f"Expected schema_version 2.0.0, got {data['schema_version']}")

        # Validate each skill
        if "skills" in data and isinstance(data["skills"], list):
            for i, skill in enumerate(data["skills"]):
                skill_errors = self.validate_skill(skill)
                for error in skill_errors:
                    errors.append(f"skills[{i}].{error}")

        return errors

    def validate_sources_json(self, data: dict[str, Any]) -> list[str]:
        """Validate sources.json file."""
        errors = []

        # Check schema_version
        if "schema_version" not in data:
            errors.append("Missing schema_version")
        elif data["schema_version"] != "2.0.0":
            errors.append(f"Expected schema_version 2.0.0, got {data['schema_version']}")

        # Validate each source
        if "repositories" in data and isinstance(data["repositories"], list):
            for i, source in enumerate(data["repositories"]):
                source_errors = self.validate_source(source)
                for error in source_errors:
                    errors.append(f"repositories[{i}].{error}")

        return errors

    def validate_file(self, filepath: Path) -> tuple[bool, list[str]]:
        """
        Validate an index file.

        Returns:
            (success, errors): True if valid, list of error messages
        """
        if not filepath.exists():
            return False, [f"File not found: {filepath}"]

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]

        # Determine file type and validate
        filename = filepath.name
        if filename == "skills.json":
            errors = self.validate_skills_json(data)
        elif filename == "sources.json":
            errors = self.validate_sources_json(data)
        elif filename == "stats.json":
            errors = self.validate_stats(data)
        else:
            return False, [f"Unknown file type: {filename}"]

        return len(errors) == 0, errors


def validate_index(index_dir: Path | None = None) -> tuple[bool, dict[str, list[str]]]:
    """
    Validate all index files.

    Args:
        index_dir: Path to index directory (defaults to ./index)

    Returns:
        (all_valid, errors_by_file): True if all files valid, dict of errors by filename
    """
    if index_dir is None:
        index_dir = Path.cwd() / "index"

    validator = SchemaValidator()
    files_to_check = ["skills.json", "sources.json", "stats.json"]

    errors_by_file: dict[str, list[str]] = {}
    all_valid = True

    for filename in files_to_check:
        filepath = index_dir / filename
        success, errors = validator.validate_file(filepath)
        if not success:
            all_valid = False
            errors_by_file[filename] = errors

    return all_valid, errors_by_file
