#!/usr/bin/env python3
"""Source repository management for Skill Atlas."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def verify_repo_exists(url: str) -> bool:
    """
    Verify a git repository exists using git ls-remote.

    Args:
        url: Repository URL to check

    Returns:
        True if repository exists and is accessible
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def map_seed_to_source(seed: dict[str, Any], added_at: str) -> dict[str, Any]:
    """
    Map a seed entry from seed-batch-1.json to a source entry for sources.json.

    Only includes schema v2 fields, excluding observational fields.

    Args:
        seed: Seed entry from input file
        added_at: ISO 8601 timestamp for when source was added

    Returns:
        Source entry dict with schema v2 fields
    """
    # Parse owner_type: take first word before space or slash
    owner_type = seed["owner_type"]
    if " " in owner_type:
        owner_type = owner_type.split()[0]
    if "/" in owner_type:
        owner_type = owner_type.split("/")[0]

    source: dict[str, Any] = {
        "id": seed["id"],
        "url": seed["url"],
        "owner_type": owner_type,
        "tier": seed["tier"],
        "status": "active",  # Will be set to "missing" if git ls-remote fails
        "added_at": added_at,
        "last_crawled_commit": None,
        "last_crawled_at": None,
        "verified": False,
    }

    # Include patterns (required by schema)
    if "include_patterns" in seed:
        source["include_patterns"] = seed["include_patterns"]

    # Optional fields
    if "exclude_patterns" in seed and seed["exclude_patterns"]:
        source["exclude_patterns"] = seed["exclude_patterns"]

    if "pattern_notes" in seed and seed.get("pattern_notes"):
        # Pattern notes go into general notes field
        if "notes" not in source:
            source["notes"] = seed["pattern_notes"]

    if "policy" in seed and seed.get("policy"):
        source["policy"] = seed["policy"]

    # Combine notes from various fields into a single notes field
    notes_parts = []
    if seed.get("pattern_notes"):
        notes_parts.append(f"Pattern: {seed['pattern_notes']}")
    if seed.get("curated_policy") and seed["curated_policy"] != "allow":
        notes_parts.append(f"Curated policy: {seed['curated_policy']}")
    if seed.get("curated_eligible_note"):
        notes_parts.append(f"Eligible: {seed['curated_eligible_note']}")

    if notes_parts:
        source["notes"] = " | ".join(notes_parts)
    else:
        source["notes"] = None

    return source


def import_sources(input_file: str | Path) -> int:
    """
    Import sources from a JSON file into index/sources.json.

    For each source:
    - Verifies repository exists with git ls-remote
    - Sets status to "missing" if repo doesn't exist
    - Only writes schema v2 fields (no observational fields)
    - Sets all entries to verified=false

    Args:
        input_file: Path to JSON file with sources to import

    Returns:
        Number of sources imported

    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If input file is not valid JSON
        ValueError: If input file format is invalid
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Load input file
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    if "seeds" not in data:
        raise ValueError("Input file must have 'seeds' array")

    seeds = data["seeds"]
    if not isinstance(seeds, list):
        raise ValueError("'seeds' must be an array")

    # Generate timestamp for added_at
    added_at = datetime.now(timezone.utc).isoformat()

    # Process each seed
    sources = []
    print(f"Importing {len(seeds)} sources...")

    for i, seed in enumerate(seeds, 1):
        seed_id = seed.get("id", f"<unknown-{i}>")
        print(f"[{i}/{len(seeds)}] Processing {seed_id}...", end=" ")

        # Map to source format
        source = map_seed_to_source(seed, added_at)

        # Verify repository exists
        url = source["url"]
        if verify_repo_exists(url):
            print("✓ verified")
        else:
            print("✗ missing")
            source["status"] = "missing"

        sources.append(source)

    # Load existing sources.json
    index_dir = Path.cwd() / "index"
    sources_path = index_dir / "sources.json"

    if sources_path.exists():
        with open(sources_path, encoding="utf-8") as f:
            sources_data = json.load(f)
    else:
        sources_data = {
            "schema_version": "2.0.0",
            "generated_at": added_at,
            "description": "Skill Atlas — Repository and source catalog. Early preview: sources are being registered.",
            "total_repositories": 0,
            "repositories": [],
        }

    # Update with new sources
    sources_data["repositories"] = sources
    sources_data["total_repositories"] = len(sources)
    sources_data["generated_at"] = added_at

    # Write back to sources.json
    with open(sources_path, "w", encoding="utf-8") as f:
        json.dump(sources_data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Add trailing newline

    return len(sources)
