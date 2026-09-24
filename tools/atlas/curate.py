"""Curate skills into the curated/ directory."""

import json
import shutil
from pathlib import Path
from typing import Any

# Whitelist of text file extensions allowed in curated skills
TEXT_EXTENSIONS = {".md", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml", ".txt"}

# Max file size for curated content (1 MB)
MAX_FILE_SIZE = 1024 * 1024

# Max word count for SKILL.md (approximate, counting whitespace-separated tokens)
MAX_SKILL_MD_WORDS = 5000


def count_words(text: str) -> int:
    """Count words in text (whitespace-separated tokens)."""
    return len(text.split())


def is_text_file(path: Path) -> bool:
    """Check if a file has a text extension from the whitelist."""
    # Allow common text files without extensions
    allowed_no_extension = {
        "LICENSE",
        "LICENCE",
        "COPYING",
        "NOTICE",
        "AUTHORS",
        "CONTRIBUTORS",
        "README",
        "ATTRIBUTION",
    }
    if path.name in allowed_no_extension or path.name.upper() in allowed_no_extension:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def check_file_size(path: Path, max_size: int = MAX_FILE_SIZE) -> bool:
    """Check if a file is within size limit."""
    return path.stat().st_size <= max_size


def is_valid_for_curation(skill_record: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Check if a skill meets all auto-curation criteria.

    Returns:
        (is_valid, list_of_reasons_if_not_valid)
    """
    reasons = []

    # Check tier 1
    if skill_record.get("trust_tier") != "official":
        reasons.append("not tier 1 (official)")

    # Check license class
    license_info = skill_record.get("license", {})
    if license_info.get("class") != "allow":
        reasons.append(f"license class is {license_info.get('class', 'unknown')}, not 'allow'")

    # Check conformance
    conformance = skill_record.get("conformance", {})
    if not conformance.get("strict"):
        reasons.append("conformance.strict is not true")

    # Check for duplicates
    dedup_info = skill_record.get("dedup", {})
    if dedup_info.get("duplicate_of"):
        reasons.append(f"is a duplicate of {dedup_info['duplicate_of']}")

    return (len(reasons) == 0, reasons)


def validate_skill_directory(skill_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate that a skill directory meets curation requirements.

    Checks:
    - Only text files with whitelist extensions
    - Each file ≤ 1MB
    - SKILL.md ≤ 5000 words

    Returns:
        (is_valid, list_of_violations)
    """
    violations = []

    if not skill_dir.exists():
        return (False, ["directory does not exist"])

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return (False, ["SKILL.md not found"])

    # Check SKILL.md word count
    skill_content = skill_md.read_text(encoding="utf-8")
    word_count = count_words(skill_content)
    if word_count > MAX_SKILL_MD_WORDS:
        violations.append(f"SKILL.md has {word_count} words (max {MAX_SKILL_MD_WORDS})")

    # Check all files in directory
    for file_path in skill_dir.rglob("*"):
        if file_path.is_file():
            # Check extension
            if not is_text_file(file_path):
                violations.append(f"{file_path.relative_to(skill_dir)}: not a text file (extension {file_path.suffix})")

            # Check size
            if not check_file_size(file_path):
                size_mb = file_path.stat().st_size / (1024 * 1024)
                violations.append(f"{file_path.relative_to(skill_dir)}: {size_mb:.2f}MB (max 1MB)")

    return (len(violations) == 0, violations)


def create_attribution(skill_record: dict[str, Any], modifications: str = "none") -> str:
    """
    Create ATTRIBUTION.md content for a curated skill.

    Args:
        skill_record: The skill record from skills.jsonl
        modifications: Description of modifications made ("none" or "UTF-8/LF normalization only")

    Returns:
        Content for ATTRIBUTION.md
    """
    source = skill_record.get("source", {})
    license_info = skill_record.get("license", {})

    # Build upstream URL
    repo = source.get("repo", "")
    commit = source.get("commit", "")
    path = source.get("path", "")

    upstream_url = f"https://github.com/{repo}/tree/{commit}/{path}" if repo and commit and path else ""

    # Copyright holder - try to extract from license or use repo owner
    copyright_holder = repo.split("/")[0] if repo else "Unknown"

    attribution = f"""# Attribution

This skill is mirrored from an upstream repository with permission under its open-source license.

**Upstream Repository:** {repo}
**Path:** {path}
**Commit:** {commit}
**URL:** {upstream_url}

**Copyright:** {copyright_holder}
**License:** {license_info.get("spdx", "See LICENSE")}
**Modifications:** {modifications}

The upstream LICENSE file is included verbatim in this directory.
"""

    return attribution


def find_license_file(source_dir: Path) -> Path | None:
    """Find LICENSE file in the skill directory or upstream location."""
    # Common license file names
    license_names = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt", "LICENCE.md"]

    # Check in skill directory
    for name in license_names:
        license_file = source_dir / name
        if license_file.exists():
            return license_file

    # Check parent directories up to root
    current = source_dir.parent
    while current.name:  # Stop at repository root
        for name in license_names:
            license_file = current / name
            if license_file.exists():
                return license_file
        current = current.parent

    return None


def mirror_skill(
    skill_record: dict[str, Any], source_dir: Path, curated_base: Path, dry_run: bool = False
) -> tuple[bool, str]:
    """
    Mirror a skill to the curated/ directory.

    Args:
        skill_record: The skill record from skills.jsonl
        source_dir: Path to the source skill directory (from crawled data)
        curated_base: Base path for curated/ directory
        dry_run: If True, only validate without copying

    Returns:
        (success, message)
    """
    # Validate skill directory
    is_valid, violations = validate_skill_directory(source_dir)
    if not is_valid:
        return (False, f"Validation failed: {'; '.join(violations)}")

    # Build target path: curated/<owner>/<repo>/<skill-dir-path>/
    source = skill_record.get("source", {})
    repo = source.get("repo", "")
    path = source.get("path", ".")

    if not repo:
        return (False, "No repository information in skill record")

    owner, repo_name = repo.split("/", 1)
    target_dir = curated_base / owner / repo_name / path

    if dry_run:
        return (True, f"Would mirror to {target_dir.relative_to(curated_base.parent)}")

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all files
    for item in source_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(source_dir)
            target_file = target_dir / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target_file)

    # Find and copy LICENSE
    license_file = find_license_file(source_dir)
    if license_file:
        target_license = target_dir / "LICENSE"
        if not target_license.exists():
            shutil.copy2(license_file, target_license)
    else:
        return (False, "No LICENSE file found in source")

    # Check for NOTICE file
    notice_file = source_dir / "NOTICE"
    if notice_file.exists():
        target_notice = target_dir / "NOTICE"
        shutil.copy2(notice_file, target_notice)

        # Also append to curated/NOTICE
        curated_notice = curated_base / "NOTICE"
        with open(curated_notice, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- From {repo}/{path} ---\n")
            f.write(notice_file.read_text(encoding="utf-8"))

    # Create ATTRIBUTION.md
    attribution_content = create_attribution(skill_record, modifications="none")
    attribution_file = target_dir / "ATTRIBUTION.md"
    attribution_file.write_text(attribution_content, encoding="utf-8")

    return (True, f"Successfully mirrored to {target_dir.relative_to(curated_base.parent)}")


def load_skills_index(index_path: Path) -> list[dict[str, Any]]:
    """Load skills from skills.jsonl or skills.json."""
    if not index_path.exists():
        return []

    # Try .jsonl first
    jsonl_path = index_path.parent / "skills.jsonl"
    if jsonl_path.exists():
        skills = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    skills.append(json.loads(line))
        return skills

    # Fall back to .json
    json_path = index_path.parent / "skills.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("skills", [])

    return []


def curate_by_id(skill_id: str, workspace: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Curate a specific skill by ID.

    Args:
        skill_id: The skill ID (e.g., "github.com/owner/repo/path")
        workspace: Workspace root path
        dry_run: If True, only validate without copying

    Returns:
        (success, message)
    """
    index_path = workspace / "index" / "skills.jsonl"
    skills = load_skills_index(index_path)

    # Find skill
    skill = None
    for s in skills:
        if s.get("id") == skill_id:
            skill = s
            break

    if not skill:
        return (False, f"Skill not found: {skill_id}")

    # Check if already curated
    if skill.get("curated_path"):
        return (False, f"Skill already curated at {skill['curated_path']}")

    # Validate curation criteria
    is_valid, reasons = is_valid_for_curation(skill)
    if not is_valid:
        return (False, f"Does not meet curation criteria: {'; '.join(reasons)}")

    # For now, since we don't have actual crawled data, we just validate
    # In a real implementation, this would mirror from build/raw/ or state/
    return (True, f"Skill {skill_id} is valid for curation")


def curate_auto_tier1(
    workspace: Path, max_total: int = 40, max_per_source: int = 3, dry_run: bool = False
) -> tuple[int, list[str]]:
    """
    Auto-curate tier 1 skills that meet all criteria.

    Args:
        workspace: Workspace root path
        max_total: Maximum total skills to curate
        max_per_source: Maximum skills per source
        dry_run: If True, only list candidates without copying

    Returns:
        (count_curated, list_of_messages)
    """
    index_path = workspace / "index" / "skills.jsonl"
    skills = load_skills_index(index_path)

    if not skills:
        return (0, ["No skills found in index"])

    # Filter candidates
    candidates = []
    for skill in skills:
        # Skip already curated
        if skill.get("curated_path"):
            continue

        is_valid, reasons = is_valid_for_curation(skill)
        if is_valid:
            candidates.append(skill)

    if not candidates:
        return (0, ["No skills meet auto-curation criteria"])

    # Group by source
    by_source: dict[str, list[dict[str, Any]]] = {}
    for skill in candidates:
        source_id = skill.get("source", {}).get("source_id", "unknown")
        if source_id not in by_source:
            by_source[source_id] = []
        by_source[source_id].append(skill)

    # Select up to max_per_source from each source
    selected = []
    for source_id, source_skills in sorted(by_source.items()):
        # Prefer skills with clear descriptions and no scripts
        source_skills_sorted = sorted(
            source_skills,
            key=lambda s: (
                len(s.get("description", "")) > 40,  # Has decent description
                "scripts" not in str(s.get("source", {}).get("path", "")),  # No scripts in path
                -len(s.get("description", "")),  # Longer description (but not too long)
            ),
            reverse=True,
        )

        selected.extend(source_skills_sorted[:max_per_source])

        if len(selected) >= max_total:
            selected = selected[:max_total]
            break

    # Generate messages
    messages = [f"Found {len(candidates)} candidates meeting criteria"]
    messages.append(f"Selected {len(selected)} skills (max {max_per_source} per source, max {max_total} total)")

    if dry_run:
        messages.append("\nCandidates for curation:")
        for skill in selected:
            skill_id = skill.get("id", "unknown")
            desc = skill.get("description", "")[:80]
            messages.append(f"  - {skill_id}: {desc}")

    return (len(selected), messages)


def cmd_curate(args, workspace: Path) -> int:
    """
    Handle the curate subcommand.

    Args:
        args: Parsed command-line arguments
        workspace: Workspace root path

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    dry_run = args.dry_run

    if args.id:
        # Curate specific skill by ID
        success, message = curate_by_id(args.id, workspace, dry_run)
        print(message)
        return 0 if success else 1

    elif args.auto_tier1:
        # Auto-curate tier 1 skills
        count, messages = curate_auto_tier1(
            workspace, max_total=args.max_total, max_per_source=args.max_per_source, dry_run=dry_run
        )
        for message in messages:
            print(message)
        return 0

    else:
        print("Error: Must specify either --id or --auto-tier1")
        return 1
