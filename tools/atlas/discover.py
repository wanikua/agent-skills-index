"""Discovery module for finding skill repositories from aggregator READMEs."""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Candidate:
    """Represents a discovered skill repository candidate."""

    repo_url: str
    evidence: str
    path_hints: list[str] | None = None
    source_aggregator: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSONL output."""
        result: dict[str, Any] = {
            "repo_url": self.repo_url,
            "evidence": self.evidence,
        }
        if self.path_hints:
            result["path_hints"] = self.path_hints
        if self.source_aggregator:
            result["source_aggregator"] = self.source_aggregator
        return result


def extract_github_links(readme_text: str) -> list[str]:
    """
    Extract GitHub repository URLs from README markdown.

    Looks for:
    - Direct repo links: https://github.com/owner/repo
    - Markdown links: [text](https://github.com/owner/repo)
    - Paths may include trailing slashes, /tree/<branch>, etc. - we normalize to base repo URL
    """
    # Pattern to match GitHub repository URLs
    # Matches: github.com/owner/repo (with optional https, trailing content, etc.)
    pattern = r"(?:https?://)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)"

    matches = re.findall(pattern, readme_text, re.IGNORECASE)

    # Normalize to https://github.com/owner/repo format
    # Use a dict to deduplicate case-insensitively while preserving first-seen case
    urls_dict: dict[str, str] = {}
    for owner, repo in matches:
        # Clean up repo name (remove .git, trailing path components, etc.)
        repo_clean = repo.split("/")[0].split("#")[0]
        # Remove .git suffix if present
        if repo_clean.endswith(".git"):
            repo_clean = repo_clean[:-4]
        # Skip common non-repo matches
        if repo_clean.lower() in {"", "compare", "issues", "pulls", "actions", "settings"}:
            continue

        url = f"https://github.com/{owner}/{repo_clean}"
        url_lower = url.lower()
        # Keep first occurrence (case-preserved)
        if url_lower not in urls_dict:
            urls_dict[url_lower] = url

    return sorted(urls_dict.values())


def fetch_readme_from_repo(repo_url: str) -> str | None:
    """
    Fetch README from a GitHub repository using git.

    Args:
        repo_url: Repository URL (e.g., https://github.com/owner/repo)

    Returns:
        README content as string, or None if not found
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Clone with minimal data
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", repo_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None

            # Try to read README.md
            for readme_name in ["README.md", "readme.md", "Readme.md", "README.MD"]:
                try:
                    result = subprocess.run(
                        ["git", "-C", tmpdir, "show", f"HEAD:{readme_name}"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        return result.stdout
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    continue

            return None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            return None


def discover_from_aggregator(aggregator_id: str, aggregator_url: str) -> list[Candidate]:
    """
    Discover skill repositories from an aggregator README.

    Args:
        aggregator_id: Identifier for the aggregator (e.g., "voltagent-awesome-agent-skills")
        aggregator_url: URL of the aggregator repository

    Returns:
        List of discovered candidates
    """
    readme = fetch_readme_from_repo(aggregator_url)
    if not readme:
        print(f"Warning: Could not fetch README from {aggregator_url}")
        return []

    github_links = extract_github_links(readme)

    # Filter out the aggregator itself and common meta-repositories
    excluded = {
        aggregator_url.lower(),
        "https://github.com/github/copilot",
        "https://github.com/anthropics/anthropic-sdk-python",
        "https://github.com/openai/openai-python",
    }

    candidates = []
    for url in github_links:
        if url.lower() not in excluded:
            # Infer path hints based on common patterns
            path_hints = []
            url_lower = url.lower()
            if "skill" in url_lower or "agent" in url_lower or "plugin" in url_lower:
                path_hints = ["skills/*/SKILL.md", "plugins/*/skills/*/SKILL.md"]

            candidates.append(
                Candidate(
                    repo_url=url,
                    evidence=f"Found in {aggregator_id} README",
                    path_hints=path_hints if path_hints else None,
                    source_aggregator=aggregator_id,
                )
            )

    return candidates


def run_discover(output_path: Path) -> int:
    """
    Run the discovery process for tier-3 aggregators.

    Args:
        output_path: Path to write candidates.jsonl

    Returns:
        Exit code (0 for success)
    """
    # Define tier-3 aggregators from seed-batch-1.json
    aggregators = [
        ("voltagent-awesome-agent-skills", "https://github.com/VoltAgent/awesome-agent-skills"),
        ("travisvn-awesome-claude-skills", "https://github.com/travisvn/awesome-claude-skills"),
    ]

    all_candidates: list[Candidate] = []

    print("Discovering skill repositories from aggregator READMEs...\n")

    for aggregator_id, aggregator_url in aggregators:
        print(f"Processing {aggregator_id}...")
        candidates = discover_from_aggregator(aggregator_id, aggregator_url)
        print(f"  Found {len(candidates)} candidates")
        all_candidates.extend(candidates)

    # Deduplicate by repo_url
    seen_urls = set()
    unique_candidates = []
    for candidate in all_candidates:
        if candidate.repo_url not in seen_urls:
            seen_urls.add(candidate.repo_url)
            unique_candidates.append(candidate)

    print(f"\nTotal unique candidates: {len(unique_candidates)}")

    # Write to JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for candidate in unique_candidates:
            json.dump(candidate.to_dict(), f)
            f.write("\n")

    print(f"\nWrote candidates to {output_path}")
    return 0
