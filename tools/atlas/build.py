#!/usr/bin/env python3
"""Build index files from crawled skill data."""

import hashlib
import json
import logging
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tools.atlas import check_refs, frontmatter, quality

logger = logging.getLogger(__name__)


def normalize_content_for_hash(content: str, frontmatter_dict: dict[str, Any] | None = None) -> str:
    """
    Normalize SKILL.md content for content_hash computation.

    Steps:
    1. Remove BOM
    2. Unicode NFC normalization
    3. CRLF -> LF
    4. Strip trailing whitespace from each line
    5. Ensure single trailing newline
    6. If frontmatter present, remove provenance keys and re-serialize sorted

    Args:
        content: Raw SKILL.md content
        frontmatter_dict: Parsed frontmatter (if available, will be normalized)

    Returns:
        Normalized content string
    """
    # Remove BOM
    if content.startswith("\ufeff"):
        content = content[1:]

    # Unicode NFC
    content = unicodedata.normalize("NFC", content)

    # CRLF -> LF
    content = content.replace("\r\n", "\n")

    # Strip trailing whitespace from each line
    lines = content.split("\n")
    lines = [line.rstrip() for line in lines]

    # Ensure single trailing newline
    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"

    # Handle frontmatter normalization if present
    if frontmatter_dict is not None and content.startswith("---\n"):
        # Find end of frontmatter
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            # Remove provenance keys
            cleaned_fm = {k: v for k, v in frontmatter_dict.items() if not _is_provenance_key(k)}

            # Re-serialize with sorted keys
            normalized_fm = yaml.dump(
                cleaned_fm, allow_unicode=True, default_flow_style=False, sort_keys=True, width=120
            )
            content = f"---\n{normalized_fm}---\n{parts[1]}"

    return content


def _is_provenance_key(key: str) -> bool:
    """Check if a frontmatter key is a provenance key to be removed."""
    provenance_prefixes = ["metadata.github-", "local-path", "mintlify-proj"]
    for prefix in provenance_prefixes:
        if key.startswith(prefix):
            return True
    return False


def compute_content_hash(content: str, frontmatter_dict: dict[str, Any] | None = None) -> str:
    """
    Compute content_hash for a skill.

    Args:
        content: Raw SKILL.md content
        frontmatter_dict: Parsed frontmatter

    Returns:
        Content hash in format "sha256:<hex>"
    """
    normalized = normalize_content_for_hash(content, frontmatter_dict)
    hash_bytes = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{hash_bytes}"


def load_existing_index(index_file: Path) -> dict[str, dict[str, Any]]:
    """
    Load existing index/skills.jsonl to inherit timestamps.

    Returns:
        Dict mapping skill id to existing record
    """
    existing = {}
    if not index_file.exists():
        return existing

    try:
        with open(index_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                skill = json.loads(line)
                if "id" in skill:
                    existing[skill["id"]] = skill
    except Exception as e:
        logger.warning(f"Failed to load existing index: {e}")

    return existing


def determine_trust_tier(source: dict[str, Any], content_hash: str, all_content_hashes: dict[str, list[str]]) -> str:
    """
    Determine trust tier for a skill.

    Rules:
    - source owner_type == vendor -> official
    - source tier == 2 -> community
    - tier 3 with content_hash matching another repo -> aggregator-copy
    - else -> unreviewed

    Args:
        source: Source record from sources.json
        content_hash: Content hash of this skill
        all_content_hashes: Dict mapping content_hash to list of source_ids

    Returns:
        Trust tier string
    """
    if source.get("owner_type") == "vendor":
        return "official"

    tier = source.get("tier", 3)
    if tier == 2:
        return "community"

    if tier == 3:
        # Check if this content_hash appears in other sources
        sources_with_hash = all_content_hashes.get(content_hash, [])
        if len(sources_with_hash) > 1:
            return "aggregator-copy"

    return "unreviewed"


def resolve_license_from_crawl(
    content: str, frontmatter_license: str | None, license_files: list[str]
) -> dict[str, Any]:
    """
    Simplified license resolution for build process using crawled metadata.

    Args:
        content: SKILL.md content
        frontmatter_license: License from frontmatter
        license_files: List of license file paths from crawl

    Returns:
        License info dict with keys: declared, spdx, evidence, file, class
    """
    # For now, use a simplified approach based on frontmatter
    # TODO: Integrate with full license resolver when file access is available

    if not frontmatter_license:
        return {
            "declared": "",
            "spdx": "NOASSERTION",
            "evidence": "none",
            "file": None,
            "class": "unknown",
        }

    # Normalize and classify
    from tools.atlas.license import LicenseClassifier

    classifier = LicenseClassifier()
    normalized = classifier.normalize(frontmatter_license)

    # Check if it starts with "Proprietary"
    if frontmatter_license.startswith("Proprietary") or (normalized and normalized.startswith("Proprietary")):
        return {
            "declared": frontmatter_license,
            "spdx": "LicenseRef-Proprietary",
            "evidence": "frontmatter",
            "file": None,
            "class": "deny",
        }

    if not normalized:
        return {
            "declared": frontmatter_license,
            "spdx": "NOASSERTION",
            "evidence": "frontmatter",
            "file": None,
            "class": "unknown",
        }

    # Try to parse as SPDX
    from license_expression import get_spdx_licensing

    licensing = get_spdx_licensing()
    try:
        parsed = licensing.parse(normalized, validate=True)
        spdx = str(parsed)
    except Exception:
        spdx = "LicenseRef-Unrecognized"

    # Classify
    lic_class, needs_review = classifier.classify(spdx)

    # Determine evidence
    evidence = "frontmatter"
    lic_file = None

    # Check if frontmatter points to a file
    if "LICENSE" in frontmatter_license.upper() and not any(
        word in frontmatter_license for word in ["http", "www", "://"]
    ):
        evidence = "skill-file"
        lic_file = license_files[0] if license_files else None

    return {
        "declared": frontmatter_license,
        "spdx": spdx,
        "evidence": evidence,
        "file": lic_file,
        "class": lic_class,
    }


def generate_install_commands(skill_id: str, source_repo: str) -> dict[str, str | None]:
    """
    Generate install commands for a skill.

    For now, returns None for all commands since we can't verify CLI syntax.
    TODO: Verify with `npx skills --help` and `gh skill --help` when available.

    Args:
        skill_id: Skill ID
        source_repo: Source repository

    Returns:
        Dict with npx, gh, claude_plugin keys (values may be None)
    """
    # TODO: Verify CLI syntax before generating commands
    # For now, return None for unverifiable commands per the red lines
    return {"npx": None, "gh": None, "claude_plugin": None}


def build_skill_record(
    raw_skill: dict[str, Any],
    source: dict[str, Any],
    sources_by_id: dict[str, dict[str, Any]],
    existing_records: dict[str, dict[str, Any]],
    all_content_hashes: dict[str, list[str]],
    now: datetime,
    check_external_refs: bool = False,
    ref_checker: check_refs.ReferenceChecker | None = None,
) -> dict[str, Any] | None:
    """
    Build a complete skill record from crawled data.

    Args:
        raw_skill: Raw skill record from crawl output
        source: Source record from sources.json
        sources_by_id: All sources by ID
        existing_records: Existing skill records (for timestamp inheritance)
        all_content_hashes: Content hash to source_id mapping
        now: Current timestamp

    Returns:
        Complete skill record or None if parsing failed
    """
    try:
        # Build skill ID
        repo = source["url"].replace("https://github.com/", "").lower()
        skill_dir = raw_skill["skill_dir"]
        skill_id = f"github.com/{repo}/{skill_dir}"

        # Parse frontmatter
        content = raw_skill["content"]
        fm_result = frontmatter.parse_content(content, skill_dir)

        # Resolve license (simplified for build process)
        license_result = resolve_license_from_crawl(
            content=content,
            frontmatter_license=fm_result.get("frontmatter", {}).get("license"),
            license_files=raw_skill.get("license_files", []),
        )

        # Compute content hash
        content_hash = compute_content_hash(content, fm_result.get("frontmatter"))

        # Run quality linting
        quality_result = quality.lint_quality(
            skill_md_path=None,
            content=content,
            name=fm_result.get("frontmatter", {}).get("name"),
            description=fm_result.get("frontmatter", {}).get("description"),
        )

        # Run security scan (S2-4)
        from tools.atlas import security

        description = fm_result.get("frontmatter", {}).get("description")
        scripts_present = raw_skill.get("has_scripts", False)

        scan_result = security.scan_skill(
            content=content,
            description=description,
            scripts_present=scripts_present,
            commit_sha=raw_skill["commit_sha"],
            layer="source",
        )

        security_field = security.format_security_field(scan_result)

        # Determine trust tier
        trust_tier = determine_trust_tier(source, content_hash, all_content_hashes)

        # Get timestamps
        existing = existing_records.get(skill_id, {})
        first_seen = existing.get("first_seen", now.isoformat())
        last_seen = now.isoformat()

        # Check if content changed
        existing_content_hash = existing.get("hashes", {}).get("content_hash")
        if existing_content_hash == content_hash:
            last_changed = existing.get("last_changed", now.isoformat())
        else:
            last_changed = now.isoformat()

        # Determine initial status (may be overridden by reference checks)
        skill_status = "active"

        # Check external references if enabled (S2-5)
        external_refs_data = None
        if check_external_refs:
            try:
                external_refs_result = check_refs.check_skill_references(raw_skill, ref_checker)
                if external_refs_result["has_dangling"]:
                    skill_status = "dangling"
                    logger.warning(f"Skill {skill_id} has dangling references: {external_refs_result['dangling_refs']}")
                external_refs_data = external_refs_result["external_refs"]
            except Exception as e:
                logger.error(f"Failed to check references for {skill_id}: {e}")

        # Update security field with external refs from S2-5
        if external_refs_data is not None:
            security_field["external_refs"] = external_refs_data

        # Build the record
        record = {
            "id": skill_id,
            "name": fm_result.get("frontmatter", {}).get("name", ""),
            "description": fm_result.get("frontmatter", {}).get("description", ""),
            "layer": "source",  # S1-7 will promote some to curated
            "source": {
                "host": "github.com",
                "repo": repo,
                "path": skill_dir,
                "ref": source.get("ref", "main"),
                "commit": raw_skill["commit_sha"],
                "blob_sha": raw_skill["blob_sha"],
                "url": f"https://github.com/{repo}/tree/{raw_skill['commit_sha']}/{skill_dir}",
                "source_id": raw_skill["source_id"],
            },
            "hashes": {
                "skill_md_sha256": raw_skill["skill_md_sha256"],
                "content_hash": content_hash,
                "folder_sha256": raw_skill["folder_sha256"],
            },
            "frontmatter": {
                "license": fm_result.get("frontmatter", {}).get("license"),
                "compatibility": fm_result.get("frontmatter", {}).get("compatibility"),
                "allowed_tools": fm_result.get("frontmatter", {}).get("allowed_tools"),
                "metadata": fm_result.get("frontmatter", {}).get("metadata") or {},
                "extensions": fm_result.get("extensions", {}),
            },
            "conformance": {
                "strict": fm_result.get("strict", False),
                "lenient": fm_result.get("lenient", False),
                "errors": fm_result.get("errors", []) + raw_skill.get("conformance_errors", []),
                "dialects": fm_result.get("dialects", []),
            },
            "license": {
                "declared": license_result.get("declared", ""),
                "spdx": license_result.get("spdx", "NOASSERTION"),
                "evidence": license_result.get("evidence", "none"),
                "file": license_result.get("file"),
                "class": license_result.get("class", "unknown"),
            },
            "declared_version": (fm_result.get("frontmatter", {}).get("metadata") or {}).get("version"),
            "packaging": ["bare"],  # TODO: Detect other packaging formats
            "install": generate_install_commands(skill_id, repo),
            "trust_tier": trust_tier,
            "tags": [],  # TODO: Extract from content
            "signals": {"repo_stars": None},  # TODO: Fetch from GitHub API in S2
            "registry_ids": {},  # S3-7
            "security": security_field,  # S2-4 (includes external_refs from S2-5)
            "quality": {"spec_valid": fm_result.get("strict", False), "smells": quality_result.smells},  # S2-6
            "dedup": {
                "canonical_id": None,
                "duplicate_of": None,
                "near_duplicate_of": None,
                "cluster": None,
            },  # S2-2/3
            "curated_path": None,
            "status": skill_status,  # S2-5: May be "dangling" if refs don't exist
            "first_seen": first_seen,
            "last_seen": last_seen,
            "last_changed": last_changed,
        }

        return record

    except Exception as e:
        logger.error(f"Failed to build skill record for {raw_skill.get('path', 'unknown')}: {e}")
        return None


def compute_stats(skills: list[dict[str, Any]], sources_count: int, now: datetime, index_commit: str) -> dict[str, Any]:
    """
    Compute statistics from skill records.

    Args:
        skills: List of skill records
        sources_count: Number of source repositories
        now: Current timestamp
        index_commit: Git commit hash of index

    Returns:
        Stats dict
    """
    from tools.atlas.dedup import compute_canonical_count

    total_skills = len(skills)
    canonical_skills = compute_canonical_count(skills)
    curated_skills = sum(1 for s in skills if s.get("layer") == "curated")

    by_license_class = defaultdict(int)
    for skill in skills:
        lic_class = skill.get("license", {}).get("class", "unknown")
        by_license_class[lic_class] += 1

    by_trust_tier = defaultdict(int)
    for skill in skills:
        tier = skill.get("trust_tier", "unreviewed")
        by_trust_tier[tier] += 1

    strict_valid = sum(1 for s in skills if s.get("conformance", {}).get("strict", False))
    spec_strict_valid_pct = (strict_valid / total_skills * 100) if total_skills > 0 else 0.0

    # Compute tier 1 freshness (placeholder for now)
    tier1_freshness_p50_hours = None  # TODO: Compute from commit timestamps

    return {
        "schema_version": "2.0.0",
        "generated_at": now.isoformat(),
        "index_commit": index_commit,
        "total_skills": total_skills,
        "canonical_skills": canonical_skills,
        "repositories": sources_count,
        "curated_skills": curated_skills,
        "by_license_class": dict(by_license_class),
        "by_trust_tier": dict(by_trust_tier),
        "spec_strict_valid_pct": round(spec_strict_valid_pct, 2),
        "tier1_freshness_p50_hours": tier1_freshness_p50_hours,
    }


def write_changes(
    changes_file: Path, new_skills: dict[str, dict[str, Any]], existing_skills: dict[str, dict[str, Any]], now: datetime
):
    """
    Write changes to index/changes.jsonl (append-only).

    Args:
        changes_file: Path to changes.jsonl
        new_skills: New skill records by ID
        existing_skills: Existing skill records by ID
        now: Current timestamp
    """
    changes = []

    # Find added skills
    for skill_id, skill in new_skills.items():
        if skill_id not in existing_skills:
            changes.append(
                {
                    "type": "added",
                    "id": skill_id,
                    "timestamp": now.isoformat(),
                    "trust_tier": skill.get("trust_tier"),
                    "license_class": skill.get("license", {}).get("class"),
                }
            )

    # Find updated skills
    for skill_id, skill in new_skills.items():
        if skill_id in existing_skills:
            old = existing_skills[skill_id]
            new_hash = skill.get("hashes", {}).get("content_hash")
            old_hash = old.get("hashes", {}).get("content_hash")

            if new_hash != old_hash:
                change_type = "updated"

                # Check for license change
                old_lic = old.get("license", {}).get("spdx")
                new_lic = skill.get("license", {}).get("spdx")
                if old_lic != new_lic:
                    change_type = "license-changed"

                # Check for security change
                old_sec = old.get("security", {}).get("status")
                new_sec = skill.get("security", {}).get("status")
                if old_sec != new_sec:
                    change_type = "security-changed"

                changes.append(
                    {
                        "type": change_type,
                        "id": skill_id,
                        "timestamp": now.isoformat(),
                        "old_hash": old_hash,
                        "new_hash": new_hash,
                    }
                )

    # Find removed skills (mark as status: removed, delete after 30 days)
    for skill_id, old_skill in existing_skills.items():
        if skill_id not in new_skills:
            # Check if it's been 30 days since first marked as removed
            if old_skill.get("status") == "removed":
                first_removed = old_skill.get("status_changed_at")
                if first_removed:
                    # TODO: Implement 30-day deletion logic
                    pass
                # Keep the removed skill in the index
                new_skills[skill_id] = old_skill
            else:
                # Mark as removed for the first time
                changes.append({"type": "removed", "id": skill_id, "timestamp": now.isoformat()})

                # Add back to new_skills with status: removed
                removed_skill = old_skill.copy()
                removed_skill["status"] = "removed"
                removed_skill["status_changed_at"] = now.isoformat()
                removed_skill["last_seen"] = now.isoformat()
                new_skills[skill_id] = removed_skill

    # Append changes to file
    if changes:
        changes_file.parent.mkdir(parents=True, exist_ok=True)
        with open(changes_file, "a", encoding="utf-8") as f:
            for change in changes:
                f.write(json.dumps(change, ensure_ascii=False, sort_keys=True))
                f.write("\n")


def build_index(
    raw_dir: Path,
    sources_file: Path,
    index_dir: Path,
    repo_root: Path,
    check_external_refs: bool = False,
) -> dict[str, Any]:
    """
    Build index files from crawled data.

    Args:
        raw_dir: Directory containing build/raw/*.jsonl files
        sources_file: Path to index/sources.json
        index_dir: Directory for index outputs
        repo_root: Repository root
        check_external_refs: Enable external reference checking (S2-5)

    Returns:
        Build summary dict
    """
    now = datetime.now(timezone.utc)

    # Get git commit
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=False
        )
        index_commit = result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        index_commit = "unknown"

    # Load sources
    logger.info("Loading sources...")
    with open(sources_file, encoding="utf-8") as f:
        sources_data = json.load(f)
    sources_by_id = {s["id"]: s for s in sources_data.get("repositories", [])}

    # Check for deleted source owners (S2-5 critical check)
    if check_external_refs:
        logger.info("Checking source repository owners...")
        ref_checker = check_refs.ReferenceChecker()
        deleted_source_ids = []

        for source_id, source in sources_by_id.items():
            owner_exists = check_refs.check_source_owner(source, ref_checker)
            if not owner_exists:
                logger.warning(f"⚠️  Source owner deleted: {source.get('url')}")
                deleted_source_ids.append(source_id)

        if deleted_source_ids:
            logger.warning(
                f"Found {len(deleted_source_ids)} sources with deleted owners. "
                f"Skills from these sources will be marked as dangling."
            )
    else:
        ref_checker = None
        deleted_source_ids = []

    # Load existing index
    logger.info("Loading existing index...")
    existing_skills_file = index_dir / "skills.jsonl"
    existing_skills = load_existing_index(existing_skills_file)

    # Read all raw files
    logger.info("Reading raw crawl data...")
    raw_skills = []
    if raw_dir.exists():
        for raw_file in raw_dir.glob("*.jsonl"):
            with open(raw_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        raw_skills.append(json.loads(line))

    logger.info(f"Found {len(raw_skills)} raw skills from crawl")

    # Build content_hash to source_id mapping for trust tier determination
    logger.info("Building content hash index...")
    content_hash_to_sources = defaultdict(list)
    for raw_skill in raw_skills:
        content = raw_skill.get("content", "")
        fm_result = frontmatter.parse_content(content, raw_skill.get("skill_dir", "."))
        content_hash = compute_content_hash(content, fm_result.get("frontmatter"))
        content_hash_to_sources[content_hash].append(raw_skill["source_id"])

    # Build skill records
    logger.info("Building skill records...")
    skills = []
    skills_from_deleted_owners = 0

    for raw_skill in raw_skills:
        source = sources_by_id.get(raw_skill["source_id"])
        if not source:
            logger.warning(f"Source {raw_skill['source_id']} not found, skipping skill")
            continue

        # Check if this skill's source owner is deleted (critical for SkillJacking)
        if raw_skill["source_id"] in deleted_source_ids:
            # Force status to dangling for skills from deleted owners
            record = build_skill_record(
                raw_skill,
                source,
                sources_by_id,
                existing_skills,
                content_hash_to_sources,
                now,
                check_external_refs=False,  # Don't check refs if owner is already deleted
                ref_checker=None,
            )
            if record:
                record["status"] = "dangling"
                record["status_reason"] = "source_owner_deleted"
                skills.append(record)
                skills_from_deleted_owners += 1
        else:
            record = build_skill_record(
                raw_skill,
                source,
                sources_by_id,
                existing_skills,
                content_hash_to_sources,
                now,
                check_external_refs=check_external_refs,
                ref_checker=ref_checker,
            )
            if record:
                skills.append(record)

    logger.info(f"Built {len(skills)} skill records")
    if skills_from_deleted_owners > 0:
        logger.warning(f"  ⚠️  {skills_from_deleted_owners} skills from deleted owners marked as dangling")

    # Apply deduplication
    logger.info("Applying exact deduplication...")
    from tools.atlas.dedup import apply_deduplication

    skills = apply_deduplication(skills)

    # Apply near-duplicate detection (S2-3)
    logger.info("Applying near-duplicate detection...")
    from tools.atlas.neardup import apply_near_deduplication

    skills = apply_near_deduplication(skills)

    # Build skills by ID dict
    new_skills_by_id = {s["id"]: s for s in skills}

    # Write changes and update new_skills_by_id to include removed skills
    logger.info("Writing changes...")
    changes_file = index_dir / "changes.jsonl"
    write_changes(changes_file, new_skills_by_id, existing_skills, now)

    # Rebuild skills list from updated dict (now includes removed skills)
    skills = list(new_skills_by_id.values())

    # Sort by ID
    skills.sort(key=lambda s: s["id"])

    # Write skills.jsonl
    logger.info("Writing skills.jsonl...")
    skills_jsonl = index_dir / "skills.jsonl"
    index_dir.mkdir(parents=True, exist_ok=True)
    with open(skills_jsonl, "w", encoding="utf-8") as f:
        for skill in skills:
            f.write(json.dumps(skill, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    # Compute stats
    logger.info("Computing statistics...")
    stats = compute_stats(skills, len(sources_by_id), now, index_commit)

    # Write stats.json
    logger.info("Writing stats.json...")
    stats_file = index_dir / "stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    # Write skills.json (compatibility wrapper)
    logger.info("Writing skills.json...")
    skills_json = index_dir / "skills.json"

    # Check if full catalog fits in 10 MB
    skills_json_full = {
        "schema_version": "2.0.0",
        "generated_at": now.isoformat(),
        "description": "Skill Atlas — Machine-readable catalog of Agent Skills (SKILL.md).",
        "total_count": len(skills),
        "curated_count": sum(1 for s in skills if s.get("layer") == "curated"),
        "skills": skills,
    }

    full_json_str = json.dumps(skills_json_full, ensure_ascii=False, indent=2)
    full_size_mb = len(full_json_str.encode("utf-8")) / (1024 * 1024)

    if full_size_mb <= 10:
        # Write full catalog
        with open(skills_json, "w", encoding="utf-8") as f:
            f.write(full_json_str)
            f.write("\n")
    else:
        # Write only curated + tier1
        filtered_skills = [
            s for s in skills if s.get("layer") == "curated" or s.get("trust_tier") in ["official", "community"]
        ]
        skills_json_filtered = {
            "schema_version": "2.0.0",
            "generated_at": now.isoformat(),
            "description": (
                "Skill Atlas — Machine-readable catalog of Agent Skills (SKILL.md). Full catalog in skills.jsonl."
            ),
            "total_count": len(filtered_skills),
            "curated_count": sum(1 for s in filtered_skills if s.get("layer") == "curated"),
            "complete_catalog": "index/skills.jsonl",
            "skills": filtered_skills,
        }
        with open(skills_json, "w", encoding="utf-8") as f:
            json.dump(skills_json_filtered, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")

    # Generate router-lite shards
    logger.info("Generating router-lite shards...")
    from tools.atlas.router_lite import generate_router_lite
    
    router_lite_dir = index_dir / "router-lite"
    router_lite_result = generate_router_lite(skills, router_lite_dir)
    
    if not router_lite_result.get("success"):
        logger.warning(f"Router-lite generation failed: {router_lite_result.get('error', 'Unknown error')}")
    
    return {
        "success": True,
        "skills_built": len(skills),
        "sources_used": len(sources_by_id),
        "stats": stats,
        "router_lite": router_lite_result,
    }
