#!/usr/bin/env python3
"""
Wording lint for Skill Atlas.

Checks that documentation does not contain present-tense claims of being
"largest", "most complete", etc. that cannot be verified.

Goal-style statements (lines starting with "Goal:") are allowed.

Exit code 0 = pass, 1 = violations found.
"""

import re
import sys
from pathlib import Path

# Patterns that are NOT allowed (except in Goal: lines and docs/research/)
BANNED_PATTERNS = [
    # Present-tense superlative claims
    (
        r"\b(is|are)\s+(the\s+)?(largest|most\s+complete|biggest)\b",
        "present-tense superlative claim (largest/most complete)",
    ),
    # "on the internet"
    (r"\bon\s+the\s+internet\b", '"on the internet" claim'),
    # "Primary Directive"
    (r"\bprimary\s+directive\b", '"Primary Directive" language'),
    # Prescriptive "always" language
    (r"\b(always|ALWAYS)\s+(check|call|use|search)(\s+\w+)*\s+first\b", 'prescriptive "always...first" language'),
    # "first stop"
    (r"\bfirst\s+stop\b", '"first stop" language'),
    # "default registry"
    (r"\bdefault\s+registry\b", '"default registry" claim'),
]


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a file for banned wording patterns.

    Returns list of (line_number, pattern_description, line_content).
    """
    violations = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                # Skip lines that start with "Goal:" (case-insensitive)
                if re.match(r"^\s*goal\s*:", line, re.IGNORECASE):
                    continue

                # Check each banned pattern
                for pattern, description in BANNED_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append((line_num, description, line.rstrip()))

    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return []

    return violations


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent

    # Files to check
    check_paths = [
        "README.md",
        "AGENTS.md",
        "docs/architecture.md",
        "curated/README.md",
        "sources/README.md",
        "skills/skill-atlas/SKILL.md",
    ]

    # Also recursively check docs/*.md (but exclude docs/research/)
    docs_dir = repo_root / "docs"
    if docs_dir.exists():
        for md_file in docs_dir.glob("*.md"):
            rel_path = md_file.relative_to(repo_root)
            if str(rel_path) not in check_paths:
                check_paths.append(str(rel_path))

    all_violations = []

    for rel_path in check_paths:
        filepath = repo_root / rel_path

        # Skip if file doesn't exist (e.g., skills/skill-atlas/SKILL.md before S0-2)
        if not filepath.exists():
            continue

        # Skip docs/research/ directory and docs/PLAN.md (meta-documentation)
        if "docs/research/" in str(rel_path) or str(rel_path) == "docs/PLAN.md":
            continue

        violations = check_file(filepath)
        if violations:
            all_violations.append((rel_path, violations))

    # Report results
    if all_violations:
        print("❌ Wording lint FAILED\n", file=sys.stderr)
        for rel_path, violations in all_violations:
            print(f"  {rel_path}:", file=sys.stderr)
            for line_num, description, line_content in violations:
                print(f"    Line {line_num}: {description}", file=sys.stderr)
                print(f"      > {line_content}", file=sys.stderr)
        total_violations = sum(len(v) for _, v in all_violations)
        num_files = len(all_violations)
        print(f"\nFound {total_violations} violation(s) in {num_files} file(s).", file=sys.stderr)
        print("\nBanned patterns:", file=sys.stderr)
        for pattern, desc in BANNED_PATTERNS:
            print(f"  - {desc}: {pattern}", file=sys.stderr)
        print("\nNote: Lines starting with 'Goal:' are exempt.", file=sys.stderr)
        return 1
    else:
        print("✅ Wording lint passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
