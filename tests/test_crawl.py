#!/usr/bin/env python3
"""Tests for the git-based crawler."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from tools.atlas import crawl


def create_git_fixture(tmpdir: Path, files: dict[str, str | bytes], symlinks: dict[str, str] = None):
    """
    Create a git repository fixture with specified files.

    Args:
        tmpdir: Directory to create repo in
        files: Dict mapping paths to content (str or bytes)
        symlinks: Dict mapping symlink paths to targets
    """
    repo_dir = tmpdir / "repo"
    repo_dir.mkdir(parents=True)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create files
    for path, content in files.items():
        file_path = repo_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            file_path.write_text(content)
        else:
            file_path.write_bytes(content)

    # Create symlinks
    if symlinks:
        for link_path, target in symlinks.items():
            link_file = repo_dir / link_path
            link_file.parent.mkdir(parents=True, exist_ok=True)
            link_file.symlink_to(target)

    # Add all files
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True, capture_output=True)

    # Commit
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    return repo_dir


def test_basic_skill_discovery():
    """Test discovering a simple SKILL.md file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create fixture repo
        repo_dir = create_git_fixture(
            tmpdir,
            {
                "skills/test-skill/SKILL.md": """---
name: test-skill
description: A test skill for unit testing
license: MIT
---

# Test Skill

This is a test skill.
""",
                "skills/test-skill/LICENSE": "MIT License\n\nCopyright (c) 2026",
            },
        )

        # Set up crawl directories
        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        # Create source entry
        source = {
            "id": "test-repo",
            "url": str(repo_dir),
            "include_patterns": ["skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        # Crawl
        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 1
        assert result["symlinks_skipped"] == 0

        # Check output file
        output_file = output_dir / "test-repo.jsonl"
        assert output_file.exists()

        with open(output_file) as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 1
        skill = skills[0]
        assert skill["path"] == "skills/test-skill/SKILL.md"
        assert skill["skill_dir"] == "skills/test-skill"
        assert skill["has_scripts"] is False
        assert len(skill["license_files"]) == 1
        assert skill["license_files"][0]["path"] == "skills/test-skill/LICENSE"
        assert skill["conformance_errors"] == []

        # Check state file
        state_file = state_dir / "test-repo.json"
        assert state_file.exists()

        with open(state_file) as f:
            state = json.load(f)

        assert state["skills_found"] == 1
        assert state["symlinks_skipped"] == 0
        assert state["last_error"] is None


def test_lowercase_filename():
    """Test that lowercase skill.md is accepted but marked with conformance error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "skills/lowercase/skill.md": """---
name: lowercase
description: Test lowercase filename
license: MIT
---

# Lowercase
""",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-lowercase",
            "url": str(repo_dir),
            "include_patterns": ["skills/*/skill.md", "skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 1

        with open(output_dir / "test-lowercase.jsonl") as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 1
        skill = skills[0]
        assert "filename-lowercase" in skill["conformance_errors"]


def test_symlink_skipping():
    """Test that symlinks are skipped and counted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "skills/real/SKILL.md": """---
name: real
description: Real skill
license: MIT
---
""",
            },
            symlinks={
                "skills/link/SKILL.md": "../real/SKILL.md",
                "skills/link/README.md": "../real/README.md",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-symlinks",
            "url": str(repo_dir),
            "include_patterns": ["skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 1
        assert result["symlinks_skipped"] == 2  # The symlinked SKILL.md and README.md

        with open(output_dir / "test-symlinks.jsonl") as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 1
        assert skills[0]["path"] == "skills/real/SKILL.md"


def test_exclude_patterns():
    """Test that exclude patterns work correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "skills/included/SKILL.md": """---
name: included
description: Should be included
---
""",
                "skills/excluded/SKILL.md": """---
name: excluded
description: Should be excluded
---
""",
                "plugins/skill/SKILL.md": """---
name: plugin
description: Plugin copy, should be excluded
---
""",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-exclude",
            "url": str(repo_dir),
            "include_patterns": ["**/SKILL.md"],
            "exclude_patterns": ["skills/excluded/**", "plugins/**"],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 1

        with open(output_dir / "test-exclude.jsonl") as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 1
        assert skills[0]["path"] == "skills/included/SKILL.md"


def test_nested_plugins_layout():
    """Test nested plugins/*/skills/*/ layout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "plugins/notion/skills/create-page/SKILL.md": """---
name: create-page
description: Create a Notion page
---
""",
                "plugins/notion/skills/search/SKILL.md": """---
name: search
description: Search Notion
---
""",
                "plugins/slack/skills/send-message/SKILL.md": """---
name: send-message
description: Send a Slack message
---
""",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-nested",
            "url": str(repo_dir),
            "include_patterns": ["plugins/*/skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 3

        with open(output_dir / "test-nested.jsonl") as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 3
        paths = sorted([s["path"] for s in skills])
        assert paths == [
            "plugins/notion/skills/create-page/SKILL.md",
            "plugins/notion/skills/search/SKILL.md",
            "plugins/slack/skills/send-message/SKILL.md",
        ]


def test_root_level_skill():
    """Test skill at repository root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "SKILL.md": """---
name: root-skill
description: Skill at repository root
---
""",
                "LICENSE": "MIT License",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-root",
            "url": str(repo_dir),
            "include_patterns": ["SKILL.md"],
            "exclude_patterns": [],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 1

        with open(output_dir / "test-root.jsonl") as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 1
        skill = skills[0]
        assert skill["path"] == "SKILL.md"
        assert skill["skill_dir"] == "."
        assert len(skill["license_files"]) == 1
        assert skill["license_files"][0]["path"] == "LICENSE"


def test_scripts_detection():
    """Test detection of scripts directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "skills/with-scripts/SKILL.md": """---
name: with-scripts
description: Has scripts
---
""",
                "skills/with-scripts/scripts/run.sh": "#!/bin/bash\necho hello\n",
                "skills/without-scripts/SKILL.md": """---
name: without-scripts
description: No scripts
---
""",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-scripts",
            "url": str(repo_dir),
            "include_patterns": ["skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 2

        with open(output_dir / "test-scripts.jsonl") as f:
            skills = {s["path"]: s for s in (json.loads(line) for line in f)}

        assert skills["skills/with-scripts/SKILL.md"]["has_scripts"] is True
        assert skills["skills/without-scripts/SKILL.md"]["has_scripts"] is False


def test_license_file_discovery():
    """Test finding LICENSE files in skill dir and ancestors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "LICENSE": "Root MIT License",
                "plugins/notion/LICENSE": "Plugin Apache-2.0 License",
                "plugins/notion/skills/search/SKILL.md": """---
name: search
description: Search skill
---
""",
                "plugins/notion/skills/search/LICENSE": "Skill-specific MIT License",
                "NOTICE": "Root NOTICE file",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-licenses",
            "url": str(repo_dir),
            "include_patterns": ["plugins/*/skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        result = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["skills_found"] == 1

        with open(output_dir / "test-licenses.jsonl") as f:
            skills = [json.loads(line) for line in f]

        assert len(skills) == 1
        license_paths = [lf["path"] for lf in skills[0]["license_files"]]

        # Should find licenses from skill dir up to root
        assert "plugins/notion/skills/search/LICENSE" in license_paths
        assert "plugins/notion/LICENSE" in license_paths
        assert "LICENSE" in license_paths
        assert "NOTICE" in license_paths


def test_skip_unchanged():
    """Test that unchanged repos are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        repo_dir = create_git_fixture(
            tmpdir,
            {
                "skills/test/SKILL.md": """---
name: test
description: Test
---
""",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        source = {
            "id": "test-unchanged",
            "url": str(repo_dir),
            "include_patterns": ["skills/*/SKILL.md"],
            "exclude_patterns": [],
        }

        # First crawl
        result1 = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=False)
        assert result1["success"]
        assert result1["skills_found"] == 1

        # Second crawl without force should skip
        result2 = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=False)
        assert result2["success"]
        assert result2.get("skipped") is True

        # Third crawl with force should not skip
        result3 = crawl.crawl_source(source, tmpdir, state_dir, output_dir, force=True)
        assert result3["success"]
        assert result3.get("skipped") is not True
        assert result3["skills_found"] == 1


def test_folder_sha256():
    """Test folder hash computation."""
    # Create test files
    files = {
        "SKILL.md": b"skill content",
        "README.md": b"readme content",
        "helper.py": b"print('hello')",
    }

    hash1 = crawl.compute_folder_sha256(files)

    # Same files, different order (dict order shouldn't matter due to sorting)
    files2 = {
        "helper.py": b"print('hello')",
        "SKILL.md": b"skill content",
        "README.md": b"readme content",
    }

    hash2 = crawl.compute_folder_sha256(files2)

    assert hash1 == hash2

    # Different content should produce different hash
    files3 = {
        "SKILL.md": b"different content",
        "README.md": b"readme content",
        "helper.py": b"print('hello')",
    }

    hash3 = crawl.compute_folder_sha256(files3)
    assert hash1 != hash3


def test_multiple_sources():
    """Test crawling multiple sources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create two fixture repos
        repo1 = create_git_fixture(
            tmpdir / "repo1",
            {
                "skills/alpha/SKILL.md": """---
name: alpha
description: Alpha skill
---
""",
            },
        )

        repo2 = create_git_fixture(
            tmpdir / "repo2",
            {
                "skills/beta/SKILL.md": """---
name: beta
description: Beta skill
---
""",
            },
        )

        state_dir = tmpdir / "state"
        output_dir = tmpdir / "output"

        sources = [
            {
                "id": "repo1",
                "url": str(repo1),
                "include_patterns": ["skills/*/SKILL.md"],
                "exclude_patterns": [],
            },
            {
                "id": "repo2",
                "url": str(repo2),
                "include_patterns": ["skills/*/SKILL.md"],
                "exclude_patterns": [],
            },
        ]

        result = crawl.crawl_sources(sources, tmpdir, state_dir, output_dir, force=True)

        assert result["success"]
        assert result["sources_crawled"] == 2
        assert result["sources_failed"] == 0
        assert result["total_skills"] == 2

        # Check both output files exist
        assert (output_dir / "repo1.jsonl").exists()
        assert (output_dir / "repo2.jsonl").exists()


def test_pathspec_matching():
    """Test pathspec matching with various patterns."""
    # Test simple pattern
    assert crawl.match_pathspec("skills/test/SKILL.md", ["skills/*/SKILL.md"])
    assert not crawl.match_pathspec("other/test/SKILL.md", ["skills/*/SKILL.md"])

    # Test wildcard pattern
    assert crawl.match_pathspec("any/path/to/skills/test/SKILL.md", ["**/skills/*/SKILL.md"])

    # Test exclude (pathspec matches, so this returns True)
    assert crawl.match_pathspec("plugins/copy/SKILL.md", ["plugins/**"])

    # Test multiple patterns (brace expansion not supported in gitignore, so test separately)
    assert crawl.match_pathspec(
        "plugins/notion/skills/search/SKILL.md", ["plugins/*/skills/*/SKILL.md", "external_plugins/*/skills/*/SKILL.md"]
    )
    assert crawl.match_pathspec(
        "external_plugins/slack/skills/send/SKILL.md",
        ["plugins/*/skills/*/SKILL.md", "external_plugins/*/skills/*/SKILL.md"],
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
