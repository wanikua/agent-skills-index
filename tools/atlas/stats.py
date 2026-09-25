#!/usr/bin/env python3
"""Statistics rendering for README and validation."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def format_stats_block(stats: dict[str, Any]) -> str:
    """
    Format stats.json data into markdown for README.

    Includes:
    - Total skills
    - Canonical count
    - Repository count
    - Curated count
    - License-resolved ratio
    - Tier-1 freshness p50
    - Last content-change date

    Each stat should link to relevant files when possible.

    Args:
        stats: Parsed stats.json

    Returns:
        Markdown string for README stats block
    """
    lines = []

    total = stats.get("total_skills", 0)
    canonical = stats.get("canonical_skills", 0)
    repos = stats.get("repositories", 0)
    curated = stats.get("curated_skills", 0)

    # Total skills
    lines.append(f"- **Total skills indexed:** [{total:,}](index/skills.jsonl)")

    # Canonical count (after deduplication)
    if canonical != total:
        lines.append(f"- **Canonical skills:** [{canonical:,}](index/skills.jsonl) (after deduplication)")

    # Repositories
    lines.append(f"- **Source repositories:** [{repos:,}](index/sources.json)")

    # Curated skills
    lines.append(f"- **Curated skills:** [{curated:,}](curated/)")

    # License-resolved ratio
    by_license = stats.get("by_license_class", {})
    resolved = by_license.get("allow", 0) + by_license.get("conditional", 0) + by_license.get("deny", 0)
    if total > 0:
        resolved_pct = (resolved / total) * 100
        lines.append(f"- **License-resolved:** {resolved_pct:.1f}% ({resolved:,} of {total:,} skills)")

    # Tier-1 freshness p50
    tier1_p50 = stats.get("tier1_freshness_p50_hours")
    if tier1_p50 is not None:
        if tier1_p50 < 24:
            freshness_str = f"{tier1_p50:.1f} hours"
        else:
            freshness_days = tier1_p50 / 24
            freshness_str = f"{freshness_days:.1f} days"
        lines.append(f"- **Tier-1 freshness (p50):** {freshness_str}")

    # Last content-change date (from generated_at)
    generated_at = stats.get("generated_at")
    if generated_at:
        try:
            dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
            lines.append(f"- **Last updated:** {date_str}")
        except Exception:
            pass

    # Add footer note about seed status if index is empty or very small
    if total == 0:
        lines.insert(0, "*Early preview: the index is being seeded.*\n")

    return "\n".join(lines)


def update_readme_stats(readme_path: Path, stats_file: Path) -> bool:
    """
    Update README.md with stats from stats.json.

    Replaces content between <!-- atlas:stats:start --> and <!-- atlas:stats:end -->.

    Args:
        readme_path: Path to README.md
        stats_file: Path to stats.json

    Returns:
        True if updated, False if no changes needed

    Raises:
        ValueError: If markers not found or stats.json invalid
    """
    # Read stats
    if not stats_file.exists():
        raise ValueError(f"stats.json not found at {stats_file}")

    with open(stats_file, encoding="utf-8") as f:
        stats = json.load(f)

    # Generate stats block
    stats_block = format_stats_block(stats)

    # Read README
    if not readme_path.exists():
        raise ValueError(f"README.md not found at {readme_path}")

    with open(readme_path, encoding="utf-8") as f:
        readme_content = f.read()

    # Find markers
    start_marker = "<!-- atlas:stats:start -->"
    end_marker = "<!-- atlas:stats:end -->"

    if start_marker not in readme_content or end_marker not in readme_content:
        raise ValueError(f"README.md must contain {start_marker} and {end_marker} markers")

    # Extract parts
    before_match = re.search(f"(.*?{re.escape(start_marker)})", readme_content, re.DOTALL)
    after_match = re.search(f"({re.escape(end_marker)}.*)", readme_content, re.DOTALL)

    if not before_match or not after_match:
        raise ValueError("Failed to parse README markers")

    before = before_match.group(1)
    after = after_match.group(1)

    # Build new content
    new_content = f"{before}\n{stats_block}\n{after}"

    # Check if changed
    if new_content == readme_content:
        return False

    # Write back
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def validate_readme_stats(readme_path: Path, stats_file: Path) -> tuple[bool, list[str]]:
    """
    Validate that README stats block matches stats.json.

    Args:
        readme_path: Path to README.md
        stats_file: Path to stats.json

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check that files exist
    if not stats_file.exists():
        errors.append(f"stats.json not found at {stats_file}")
        return False, errors

    if not readme_path.exists():
        errors.append(f"README.md not found at {readme_path}")
        return False, errors

    # Read stats
    try:
        with open(stats_file, encoding="utf-8") as f:
            stats = json.load(f)
    except Exception as e:
        errors.append(f"Failed to parse stats.json: {e}")
        return False, errors

    # Read README
    try:
        with open(readme_path, encoding="utf-8") as f:
            readme_content = f.read()
    except Exception as e:
        errors.append(f"Failed to read README.md: {e}")
        return False, errors

    # Check markers exist
    start_marker = "<!-- atlas:stats:start -->"
    end_marker = "<!-- atlas:stats:end -->"

    if start_marker not in readme_content:
        errors.append(f"README.md missing {start_marker} marker")
        return False, errors

    if end_marker not in readme_content:
        errors.append(f"README.md missing {end_marker} marker")
        return False, errors

    # Extract current stats block
    pattern = re.escape(start_marker) + r"\s*(.*?)\s*" + re.escape(end_marker)
    match = re.search(pattern, readme_content, re.DOTALL)

    if not match:
        errors.append("Failed to extract stats block from README.md")
        return False, errors

    current_block = match.group(1).strip()

    # Generate expected stats block
    expected_block = format_stats_block(stats).strip()

    # Compare
    if current_block != expected_block:
        errors.append("README stats block does not match stats.json")
        errors.append(f"Expected:\n{expected_block}")
        errors.append(f"Found:\n{current_block}")
        return False, errors

    return True, []
