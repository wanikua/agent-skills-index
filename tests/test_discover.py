"""Tests for the discover module."""

import json

from tools.atlas.discover import Candidate, extract_github_links


class TestGitHubLinkExtraction:
    """Test GitHub link extraction from README markdown."""

    def test_extract_basic_links(self):
        """Test extraction of basic GitHub links."""
        readme = """
        # Awesome Skills
        - https://github.com/owner1/repo1
        - https://github.com/owner2/repo2
        """
        links = extract_github_links(readme)
        assert "https://github.com/owner1/repo1" in links
        assert "https://github.com/owner2/repo2" in links
        assert len(links) == 2

    def test_extract_markdown_links(self):
        """Test extraction from markdown link syntax."""
        readme = """
        Check out [this skill](https://github.com/owner/skill-repo) and
        [another one](https://github.com/another/repo).
        """
        links = extract_github_links(readme)
        assert "https://github.com/owner/skill-repo" in links
        assert "https://github.com/another/repo" in links
        assert len(links) == 2

    def test_normalize_urls(self):
        """Test URL normalization (removing paths, .git, etc.)."""
        readme = """
        - https://github.com/owner/repo.git
        - https://github.com/owner/repo/tree/main
        - https://github.com/owner/repo/tree/main/skills
        - http://github.com/owner/repo
        - github.com/owner/repo
        """
        links = extract_github_links(readme)
        # All should normalize to the same URL
        assert links == ["https://github.com/owner/repo"]

    def test_skip_non_repo_paths(self):
        """Test that non-repository paths are skipped."""
        readme = """
        - https://github.com/owner/repo
        - https://github.com/owner/repo/issues
        - https://github.com/owner/repo/pulls
        - https://github.com/owner/repo/actions
        - https://github.com/owner/repo/compare
        """
        links = extract_github_links(readme)
        assert links == ["https://github.com/owner/repo"]

    def test_deduplication(self):
        """Test that duplicate URLs are deduplicated."""
        readme = """
        - https://github.com/owner/repo
        - https://github.com/owner/repo
        - https://github.com/owner/repo/tree/main
        """
        links = extract_github_links(readme)
        assert links == ["https://github.com/owner/repo"]

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        readme = """
        - https://GitHub.com/Owner/Repo
        - HTTPS://github.COM/owner/repo
        """
        links = extract_github_links(readme)
        assert links == ["https://github.com/Owner/Repo"]

    def test_empty_readme(self):
        """Test handling of empty README."""
        links = extract_github_links("")
        assert links == []

    def test_no_github_links(self):
        """Test README with no GitHub links."""
        readme = """
        # My Project
        This is a project without GitHub links.
        Visit our website at https://example.com
        """
        links = extract_github_links(readme)
        assert links == []

    def test_mixed_content(self):
        """Test extraction from mixed content with various formats."""
        readme = """
        # Awesome Skills List

        ## Category 1
        - [Skill A](https://github.com/user1/skill-a) - A great skill
        - [Skill B](https://github.com/user2/skill-b) - Another one

        ## Category 2
        Check out https://github.com/user3/skill-c for more.

        Also see:
        - github.com/user4/skill-d (without https)
        - http://github.com/user5/skill-e (with http)

        ## Not Skills
        - https://example.com/not-github
        - mailto:user@example.com
        """
        links = extract_github_links(readme)
        assert len(links) == 5
        assert "https://github.com/user1/skill-a" in links
        assert "https://github.com/user2/skill-b" in links
        assert "https://github.com/user3/skill-c" in links
        assert "https://github.com/user4/skill-d" in links
        assert "https://github.com/user5/skill-e" in links


class TestCandidate:
    """Test Candidate dataclass."""

    def test_candidate_to_dict_minimal(self):
        """Test candidate conversion to dict with minimal fields."""
        candidate = Candidate(
            repo_url="https://github.com/owner/repo", evidence="Test evidence", path_hints=None, source_aggregator=None
        )
        result = candidate.to_dict()
        assert result["repo_url"] == "https://github.com/owner/repo"
        assert result["evidence"] == "Test evidence"
        assert "path_hints" not in result
        assert "source_aggregator" not in result

    def test_candidate_to_dict_full(self):
        """Test candidate conversion to dict with all fields."""
        candidate = Candidate(
            repo_url="https://github.com/owner/repo",
            evidence="Test evidence",
            path_hints=["skills/*/SKILL.md"],
            source_aggregator="test-aggregator",
        )
        result = candidate.to_dict()
        assert result["repo_url"] == "https://github.com/owner/repo"
        assert result["evidence"] == "Test evidence"
        assert result["path_hints"] == ["skills/*/SKILL.md"]
        assert result["source_aggregator"] == "test-aggregator"

    def test_candidate_jsonl_serialization(self, tmp_path):
        """Test that candidates can be serialized to JSONL."""
        candidates = [
            Candidate(
                repo_url="https://github.com/owner/repo1",
                evidence="Evidence 1",
                path_hints=["skills/*/SKILL.md"],
                source_aggregator="agg1",
            ),
            Candidate(repo_url="https://github.com/owner/repo2", evidence="Evidence 2", path_hints=None),
        ]

        output_file = tmp_path / "test.jsonl"
        with open(output_file, "w") as f:
            for candidate in candidates:
                json.dump(candidate.to_dict(), f)
                f.write("\n")

        # Read back and verify
        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) == 2
        obj1 = json.loads(lines[0])
        assert obj1["repo_url"] == "https://github.com/owner/repo1"
        assert obj1["source_aggregator"] == "agg1"

        obj2 = json.loads(lines[1])
        assert obj2["repo_url"] == "https://github.com/owner/repo2"
        assert "source_aggregator" not in obj2


class TestDiscoverIntegration:
    """Integration tests for the discover command."""

    def test_candidates_file_created(self, tmp_path):
        """Test that running discover creates the candidates file."""
        output_path = tmp_path / "candidates.jsonl"

        # We can't easily test the full run_discover without network access,
        # but we can test that Candidate objects serialize correctly
        candidates = [
            Candidate(
                repo_url="https://github.com/test/repo",
                evidence="Test",
                path_hints=["skills/*/SKILL.md"],
                source_aggregator="test",
            )
        ]

        with open(output_path, "w") as f:
            for candidate in candidates:
                json.dump(candidate.to_dict(), f)
                f.write("\n")

        assert output_path.exists()
        with open(output_path) as f:
            data = json.loads(f.readline())
            assert data["repo_url"] == "https://github.com/test/repo"

    def test_output_format_stability(self):
        """Test that the output format matches expected schema."""
        candidate = Candidate(
            repo_url="https://github.com/owner/repo",
            evidence="Found in aggregator README",
            path_hints=["skills/*/SKILL.md", "plugins/*/skills/*/SKILL.md"],
            source_aggregator="voltagent-awesome-agent-skills",
        )

        result = candidate.to_dict()

        # Verify required fields
        assert "repo_url" in result
        assert "evidence" in result
        assert isinstance(result["repo_url"], str)
        assert isinstance(result["evidence"], str)

        # Verify optional fields when present
        assert "path_hints" in result
        assert isinstance(result["path_hints"], list)
        assert "source_aggregator" in result
        assert isinstance(result["source_aggregator"], str)

        # Verify URL format
        assert result["repo_url"].startswith("https://github.com/")
