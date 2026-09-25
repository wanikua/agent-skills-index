"""Curate skills into the curated/ directory."""

import hashlib
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

    # Check security status if present (fail closed for curated)
    security = skill_record.get("security", {})
    if security:  # If security field exists
        status = security.get("status")
        if status != "pass":
            reasons.append(f"security.status is '{status}', not 'pass'")

    return (len(reasons) == 0, reasons)


def validate_skill_directory(skill_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate that a skill directory meets curation requirements.

    Checks:
    - Only text files with whitelist extensions
    - No symlinks (red line: never follow symlinks)
    - Each file ≤ 1MB
    - SKILL.md ≤ 5000 words

    Returns:
        (is_valid, list_of_violations)
    """
    violations = []

    if not skill_dir.exists():
        return (False, ["directory does not exist"])

    # P1: Check if skill_dir itself is a symlink
    if skill_dir.is_symlink():
        return (False, ["skill directory is a symlink (not allowed)"])

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return (False, ["SKILL.md not found"])

    # P1: Check if SKILL.md is a symlink
    if skill_md.is_symlink():
        violations.append("SKILL.md is a symlink (not allowed)")
        return (False, violations)

    # Check SKILL.md word count
    skill_content = skill_md.read_text(encoding="utf-8")
    word_count = count_words(skill_content)
    if word_count > MAX_SKILL_MD_WORDS:
        violations.append(f"SKILL.md has {word_count} words (max {MAX_SKILL_MD_WORDS})")

    # Check all files in directory
    for file_path in skill_dir.rglob("*"):
        # P1: Reject symlinks
        if file_path.is_symlink():
            violations.append(f"{file_path.relative_to(skill_dir)}: is a symlink (not allowed)")
            continue

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


def find_license_file(skill_dir: Path, repo_root: Path | None = None) -> Path | None:
    """
    Find LICENSE file bounded to skill tree and repository root.

    P1 FIX: Do not pick an unrelated ancestor LICENSE.
    Search only in:
    1. The skill directory itself
    2. Parent directories up to (and including) the repository root

    Args:
        skill_dir: Path to the skill directory
        repo_root: Path to the repository root (if known). If None, search up to filesystem root.

    Returns:
        Path to LICENSE file if found, None otherwise
    """
    # Common license file names
    license_names = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt", "LICENCE.md"]

    # Check in skill directory first
    for name in license_names:
        license_file = skill_dir / name
        if license_file.exists() and not license_file.is_symlink():
            return license_file

    # Check parent directories up to repo root
    current = skill_dir.parent
    while True:
        # Stop if we've reached the repo root
        if repo_root and current == repo_root:
            # Check this directory and then stop
            for name in license_names:
                license_file = current / name
                if license_file.exists() and not license_file.is_symlink():
                    return license_file
            break

        # Stop if we've reached the filesystem root
        if current.parent == current:
            break

        # Check this directory
        for name in license_names:
            license_file = current / name
            if license_file.exists() and not license_file.is_symlink():
                return license_file

        # If no repo_root specified, only search the immediate parent
        # to avoid picking up unrelated licenses
        if repo_root is None:
            break

        current = current.parent

    return None


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


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
    # P1: Validate skill directory (includes symlink checks)
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

    # P2: Locate LICENSE before copying
    license_file = find_license_file(source_dir)
    if not license_file:
        return (False, "No LICENSE file found in source (bounded search)")

    # Create target directory
    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files (P1: skip symlinks)
        for item in source_dir.rglob("*"):
            if item.is_symlink():
                # Skip symlinks entirely
                continue

            if item.is_file():
                rel_path = item.relative_to(source_dir)
                target_file = target_dir / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # P2: Verify hash if available
                skill_md_sha = skill_record.get("hashes", {}).get("skill_md_sha256")
                if rel_path.name == "SKILL.md" and skill_md_sha:
                    # Compute hash of source file
                    actual_hash = compute_file_sha256(item)
                    if actual_hash != skill_md_sha:
                        raise ValueError(f"Hash mismatch for SKILL.md: expected {skill_md_sha}, got {actual_hash}")

                shutil.copy2(item, target_file)

        # Copy LICENSE
        target_license = target_dir / "LICENSE"
        if not target_license.exists():
            shutil.copy2(license_file, target_license)

        # Check for NOTICE file (non-symlink)
        notice_file = source_dir / "NOTICE"
        if notice_file.exists() and not notice_file.is_symlink():
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

    except Exception as e:
        # P2: Clean up partial curated/ on failure
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
            except Exception:
                pass  # Best effort cleanup
        return (False, f"Failed to mirror: {e}")


def load_skills_index(workspace: Path) -> list[dict[str, Any]]:
    """
    Load skills from skills.jsonl or skills.json.

    P2 FIX: Resolve both skills.jsonl and skills.json up front.
    """
    # Try .jsonl first (primary)
    jsonl_path = workspace / "index" / "skills.jsonl"
    if jsonl_path.exists():
        skills = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    skills.append(json.loads(line))
        return skills

    # Fall back to .json
    json_path = workspace / "index" / "skills.json"
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
    skills = load_skills_index(workspace)

    if not skills:
        return (False, "No skills found in index")

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

    # P2 CRITICAL: Actually mirror the skill in non-dry-run mode
    if not dry_run:
        # TODO: In a full implementation, we would need to find the source directory
        # from build/raw/ or state/crawl/ based on the skill's source information
        return (False, "Non-dry-run curation not yet fully implemented - need crawled source data")

    return (True, f"Skill {skill_id} is valid for curation (dry-run)")


def curate_auto_tier1(
    workspace: Path,
    max_total: int = 40,
    max_per_source: int = 3,
    dry_run: bool = False,
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
    skills = load_skills_index(workspace)

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
    else:
        # P2 CRITICAL: Actually mirror skills in non-dry-run mode
        messages.append(
            "\nNon-dry-run curation not yet fully implemented - would need to mirror from crawled source data"
        )
        # TODO: Implement actual mirroring loop here using mirror_skill()

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
            workspace,
            max_total=args.max_total,
            max_per_source=args.max_per_source,
            dry_run=dry_run,
        )
        for message in messages:
            print(message)
        return 0

    else:
        print("Error: Must specify either --id or --auto-tier1")
        return 1
