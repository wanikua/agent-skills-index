#!/usr/bin/env python3
"""Git-based crawler for Agent Skills repositories."""

import hashlib
import json
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pathspec

logger = logging.getLogger(__name__)

# Per-repo timeout in seconds
REPO_TIMEOUT = 120

# Maximum concurrent clones
MAX_CONCURRENCY = 4


class CrawlError(Exception):
    """Error during crawling."""

    pass


def get_head_sha(url: str, timeout: int = 30) -> str | None:
    """
    Get the HEAD SHA of a remote repository.

    Args:
        url: Repository URL
        timeout: Timeout in seconds

    Returns:
        40-character SHA or None if failed
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"git ls-remote failed for {url}: {result.stderr}")
            return None

        lines = result.stdout.strip().split("\n")
        if not lines or not lines[0]:
            return None

        sha = lines[0].split()[0]
        if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
            return sha
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"git ls-remote timed out for {url}")
        return None
    except Exception as e:
        logger.error(f"git ls-remote error for {url}: {e}")
        return None


def shallow_clone(url: str, target_dir: Path, timeout: int = REPO_TIMEOUT) -> bool:
    """
    Perform a shallow blobless clone of a repository.

    Args:
        url: Repository URL
        target_dir: Directory to clone into
        timeout: Timeout in seconds

    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--no-checkout",
                url,
                str(target_dir),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"git clone failed for {url}: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"git clone timed out for {url}")
        return False
    except Exception as e:
        logger.error(f"git clone error for {url}: {e}")
        return False


def list_tree(repo_dir: Path, timeout: int = 30) -> list[dict[str, Any]] | None:
    """
    List all files in the repository tree at HEAD.

    Args:
        repo_dir: Path to cloned repository
        timeout: Timeout in seconds

    Returns:
        List of dicts with keys: mode, type, sha, path
        Returns None on error
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "ls-tree", "-r", "--full-tree", "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"git ls-tree failed: {result.stderr}")
            return None

        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Format: <mode> <type> <sha>\t<path>
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            meta, path = parts
            mode, obj_type, sha = meta.split()
            entries.append({"mode": mode, "type": obj_type, "sha": sha, "path": path})

        return entries
    except subprocess.TimeoutExpired:
        logger.error("git ls-tree timed out")
        return None
    except Exception as e:
        logger.error(f"git ls-tree error: {e}")
        return None


def get_blob_content(repo_dir: Path, blob_sha: str, timeout: int = 30) -> bytes | None:
    """
    Read blob content from git object store.

    Args:
        repo_dir: Path to cloned repository
        blob_sha: Git blob SHA
        timeout: Timeout in seconds

    Returns:
        Blob content as bytes or None on error
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "cat-file", "-p", blob_sha],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"git cat-file failed for {blob_sha}: {result.stderr}")
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error(f"git cat-file timed out for {blob_sha}")
        return None
    except Exception as e:
        logger.error(f"git cat-file error for {blob_sha}: {e}")
        return None


def match_pathspec(path: str, patterns: list[str]) -> bool:
    """
    Check if a path matches any of the given gitignore-style patterns.

    Args:
        path: File path to check
        patterns: List of patterns (gitignore syntax)

    Returns:
        True if path matches any pattern
    """
    if not patterns:
        return True

    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return spec.match_file(path)


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of data."""
    return hashlib.sha256(data).hexdigest()


def compute_folder_sha256(files: dict[str, bytes]) -> str:
    """
    Compute folder hash using vercel-labs/skills algorithm.

    Args:
        files: Dict mapping relative paths to file contents

    Returns:
        SHA-256 hex digest
    """
    # Sort files by path
    sorted_paths = sorted(files.keys())

    # Concatenate path + content for each file
    hasher = hashlib.sha256()
    for path in sorted_paths:
        hasher.update(path.encode("utf-8"))
        hasher.update(files[path])

    return hasher.hexdigest()


def find_license_files(tree_entries: list[dict[str, Any]], skill_dir: str) -> list[dict[str, str]]:
    """
    Find LICENSE-type files from skill directory up to repository root.

    Args:
        tree_entries: Full tree listing from git ls-tree
        skill_dir: Skill directory path (e.g., "skills/pdf")

    Returns:
        List of dicts with keys: path, sha
    """
    license_names = {"LICENSE", "LICENCE", "COPYING", "NOTICE"}
    skill_parts = Path(skill_dir).parts if skill_dir != "." else []

    licenses = []

    # Check skill directory and all ancestor directories up to root
    for level in range(len(skill_parts) + 1):
        if level == 0:
            check_dir = "."
        else:
            check_dir = str(Path(*skill_parts[:level]))

        for entry in tree_entries:
            entry_path = Path(entry["path"])
            entry_dir = str(entry_path.parent) if entry_path.parent != Path(".") else "."

            if entry_dir != check_dir:
                continue

            # Check if filename (ignoring extensions) is a license file
            name_parts = entry_path.name.split(".")
            base_name = name_parts[0].upper()

            if base_name in license_names:
                licenses.append({"path": entry["path"], "sha": entry["sha"]})

    return licenses


def crawl_source(
    source: dict[str, Any],
    repo_root: Path,
    state_dir: Path,
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    """
    Crawl a single source repository.

    Args:
        source: Source entry from sources.json
        repo_root: Repository root path (for relative paths)
        state_dir: Directory for state files (state/crawl/)
        output_dir: Directory for output files (build/raw/)
        force: Force crawl even if unchanged

    Returns:
        Dict with status info: success, error, skills_found, etc.
    """
    source_id = source["id"]
    url = source["url"]

    logger.info(f"Crawling {source_id}: {url}")

    # Load previous state if it exists
    state_file = state_dir / f"{source_id}.json"
    previous_state = {}
    if state_file.exists():
        try:
            with open(state_file) as f:
                previous_state = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load state for {source_id}: {e}")

    # Get HEAD SHA
    head_sha = get_head_sha(url)
    if not head_sha:
        error_msg = "Failed to get HEAD SHA"
        logger.error(f"{source_id}: {error_msg}")
        # Update state with error
        state = {
            **previous_state,
            "last_error": error_msg,
            "last_error_at": datetime.now(timezone.utc).isoformat(),
        }
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return {"success": False, "error": error_msg, "source_id": source_id}

    # Check if we can skip (unchanged and not forced)
    if not force and previous_state.get("head_sha") == head_sha:
        logger.info(f"{source_id}: Unchanged (HEAD={head_sha[:7]}), skipping")
        return {"success": True, "skipped": True, "source_id": source_id, "head_sha": head_sha}

    # Clone repository
    with tempfile.TemporaryDirectory(prefix=f"atlas-crawl-{source_id}-") as tmpdir:
        clone_dir = Path(tmpdir) / "repo"

        if not shallow_clone(url, clone_dir):
            error_msg = "Failed to clone repository"
            logger.error(f"{source_id}: {error_msg}")
            state = {
                **previous_state,
                "last_error": error_msg,
                "last_error_at": datetime.now(timezone.utc).isoformat(),
            }
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                f.write("\n")
            return {"success": False, "error": error_msg, "source_id": source_id}

        # List tree
        tree = list_tree(clone_dir)
        if tree is None:
            error_msg = "Failed to list tree"
            logger.error(f"{source_id}: {error_msg}")
            state = {
                **previous_state,
                "last_error": error_msg,
                "last_error_at": datetime.now(timezone.utc).isoformat(),
            }
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                f.write("\n")
            return {"success": False, "error": error_msg, "source_id": source_id}

        # Process tree entries
        symlinks_skipped = 0
        skills_found = []

        include_patterns = source.get("include_patterns", [])
        exclude_patterns = source.get("exclude_patterns", [])

        for entry in tree:
            # Skip symlinks
            if entry["mode"] == "120000":
                symlinks_skipped += 1
                continue

            path = entry["path"]

            # Check include patterns
            if include_patterns and not match_pathspec(path, include_patterns):
                continue

            # Check exclude patterns
            if exclude_patterns and match_pathspec(path, exclude_patterns):
                continue

            # Check if filename is SKILL.md or skill.md
            filename = Path(path).name
            if filename not in ("SKILL.md", "skill.md"):
                continue

            # Found a skill file
            skill_dir = str(Path(path).parent) if Path(path).parent != Path(".") else "."

            logger.info(f"{source_id}: Found skill at {path}")

            # Read skill content
            skill_content = get_blob_content(clone_dir, entry["sha"])
            if skill_content is None:
                logger.warning(f"{source_id}: Failed to read {path}")
                continue

            # Check for lowercase filename
            conformance_errors = []
            if filename == "skill.md":
                conformance_errors.append("filename-lowercase")

            # List files in skill directory
            skill_files = {}
            has_scripts = False

            for tree_entry in tree:
                entry_path = Path(tree_entry["path"])
                entry_dir = str(entry_path.parent) if entry_path.parent != Path(".") else "."

                # Check if this file/directory is within the skill directory
                if skill_dir == ".":
                    # Root-level skill: all files are candidates
                    is_in_skill_dir = True
                    rel_path = entry_path
                else:
                    # Check if entry is within skill_dir
                    try:
                        rel_path = entry_path.relative_to(skill_dir)
                        is_in_skill_dir = True
                    except ValueError:
                        is_in_skill_dir = False

                if not is_in_skill_dir:
                    continue

                # Check for scripts subdirectory
                parts = list(rel_path.parts)
                if "scripts" in parts:
                    has_scripts = True

                # Only include direct files in skill directory for folder hash
                if entry_dir == skill_dir:
                    # Read file content for folder hash (skip large files)
                    if tree_entry["type"] == "blob" and tree_entry["mode"] != "120000":
                        content = get_blob_content(clone_dir, tree_entry["sha"])
                        if content and len(content) < 10 * 1024 * 1024:  # 10MB limit
                            skill_files[str(rel_path)] = content

            # Add SKILL.md itself to skill_files for folder hash
            skill_files["SKILL.md"] = skill_content

            # Compute hashes
            skill_md_sha256 = compute_sha256(skill_content)
            folder_sha256 = compute_folder_sha256(skill_files)

            # Find license files
            license_files = find_license_files(tree, skill_dir)

            skill_record = {
                "source_id": source_id,
                "path": path,
                "skill_dir": skill_dir,
                "blob_sha": entry["sha"],
                "content": (
                    skill_content.decode("utf-8", errors="replace")
                    if isinstance(skill_content, bytes)
                    else skill_content
                ),
                "skill_md_sha256": skill_md_sha256,
                "folder_sha256": folder_sha256,
                "has_scripts": has_scripts,
                "license_files": license_files,
                "conformance_errors": conformance_errors,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "commit_sha": head_sha,
            }

            skills_found.append(skill_record)

        # Write output
        output_file = output_dir / f"{source_id}.jsonl"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            for skill in skills_found:
                f.write(json.dumps(skill, ensure_ascii=False))
                f.write("\n")

        # Update state
        state = {
            "source_id": source_id,
            "head_sha": head_sha,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "skills_found": len(skills_found),
            "symlinks_skipped": symlinks_skipped,
            "last_error": None,
        }

        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")

        logger.info(f"{source_id}: Found {len(skills_found)} skills, skipped {symlinks_skipped} symlinks")

        return {
            "success": True,
            "source_id": source_id,
            "head_sha": head_sha,
            "skills_found": len(skills_found),
            "symlinks_skipped": symlinks_skipped,
        }


def crawl_sources(
    sources: list[dict[str, Any]],
    repo_root: Path,
    state_dir: Path,
    output_dir: Path,
    force: bool = False,
    source_id_filter: str | None = None,
) -> dict[str, Any]:
    """
    Crawl multiple sources.

    Args:
        sources: List of source entries from sources.json
        repo_root: Repository root path
        state_dir: State directory
        output_dir: Output directory
        force: Force crawl even if unchanged
        source_id_filter: If provided, only crawl this source

    Returns:
        Summary dict with stats
    """
    # Filter sources if requested
    if source_id_filter:
        sources = [s for s in sources if s["id"] == source_id_filter]
        if not sources:
            logger.error(f"Source '{source_id_filter}' not found")
            return {"success": False, "error": f"Source '{source_id_filter}' not found"}

    results = []
    total_skills = 0
    total_errors = 0
    total_skipped = 0

    for source in sources:
        result = crawl_source(source, repo_root, state_dir, output_dir, force)
        results.append(result)

        if result.get("success"):
            if result.get("skipped"):
                total_skipped += 1
            else:
                total_skills += result.get("skills_found", 0)
        else:
            total_errors += 1

    return {
        "success": True,
        "sources_crawled": len(sources),
        "sources_skipped": total_skipped,
        "sources_failed": total_errors,
        "total_skills": total_skills,
        "results": results,
    }
