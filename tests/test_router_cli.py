"""Integration tests for router CLI commands (S3-2)."""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def test_repo(tmp_path):
    """Set up a test repository structure."""
    # Create index structure
    index_dir = tmp_path / "index"
    index_dir.mkdir()

    skills_file = index_dir / "skills.jsonl"

    # Create sample skills
    skills = [
        {
            "id": "github.com/test/repo/pdf-reader",
            "name": "pdf-reader",
            "description": "Read and extract text from PDF files",
            "layer": "curated",
            "source": {"url": "https://github.com/test/repo/tree/main/pdf-reader"},
            "hashes": {"content_hash": "sha256:abc123"},
            "install": {
                "npx": "npx skills add test/repo/pdf-reader",
                "gh": "gh skill add test/repo/pdf-reader",
                "claude_plugin": None,
            },
            "trust_tier": "official",
            "license": {"spdx": "MIT"},
            "security": {"status": "pass"},
            "tags": ["pdf", "text", "extraction"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/test/repo/pdf-reader"},
        },
        {
            "id": "github.com/test/repo/web-crawler",
            "name": "web-crawler",
            "description": "Crawl websites and extract structured data",
            "layer": "source",
            "source": {"url": "https://github.com/test/repo/tree/main/web-crawler"},
            "hashes": {"content_hash": "sha256:def456"},
            "install": {"npx": "npx skills add test/repo/web-crawler", "gh": None, "claude_plugin": None},
            "trust_tier": "community",
            "license": {"spdx": "Apache-2.0"},
            "security": {"status": "review"},
            "tags": ["web", "crawler", "scraping"],
            "status": "active",
            "dedup": {"canonical_id": "github.com/test/repo/web-crawler"},
        },
    ]

    with open(skills_file, "w", encoding="utf-8") as f:
        for skill in skills:
            f.write(json.dumps(skill, ensure_ascii=False) + "\n")

    # Create build directory
    build_dir = tmp_path / "build"
    build_dir.mkdir()

    return tmp_path


def test_atlas_index_command(test_repo):
    """Test 'atlas index' command."""
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "index"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Router database built" in result.stdout
    assert "Indexed 2 skills" in result.stdout

    # Check that database was created
    db_path = test_repo / "build" / "router.sqlite"
    assert db_path.exists()


def test_atlas_find_command_text_output(test_repo):
    """Test 'atlas find' command with text output."""
    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Search
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "pdf-reader" in result.stdout
    assert "Read and extract text from PDF files" in result.stdout
    assert "github.com/test/repo/pdf-reader" in result.stdout


def test_atlas_find_command_json_output(test_repo):
    """Test 'atlas find' command with JSON output."""
    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Search with JSON output
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Parse JSON output
    output = json.loads(result.stdout)

    assert "query" in output
    assert output["query"] == "pdf"
    assert "abstained" in output
    assert isinstance(output["abstained"], bool)
    assert "results" in output
    assert isinstance(output["results"], list)
    assert len(output["results"]) >= 1

    # Check first result
    first = output["results"][0]
    assert first["name"] == "pdf-reader"
    assert "id" in first
    assert "description" in first
    assert "install" in first
    assert "url" in first
    assert "content_hash" in first
    assert "trust_tier" in first
    assert "license" in first
    assert "security" in first
    assert "why_matched" in first
    assert "score" in first


def test_atlas_find_with_filters(test_repo):
    """Test 'atlas find' command with various filters."""
    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Test layer filter
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf", "--layer", "curated", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert len(output["results"]) >= 1

    # Test license filter
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf", "--license", "permissive", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Test trust filter
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf", "--min-trust", "official", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Test k parameter
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "web", "-k", "1", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert len(output["results"]) <= 1


def test_atlas_show_command_text_output(test_repo):
    """Test 'atlas show' command with text output."""
    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Show skill
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "show", "github.com/test/repo/pdf-reader"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "pdf-reader" in result.stdout
    assert "github.com/test/repo/pdf-reader" in result.stdout
    assert "Read and extract text from PDF files" in result.stdout
    assert "MIT" in result.stdout


def test_atlas_show_command_json_output(test_repo):
    """Test 'atlas show' command with JSON output."""
    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Show skill with JSON output
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "show", "github.com/test/repo/pdf-reader", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Parse JSON output
    output = json.loads(result.stdout)

    assert output["id"] == "github.com/test/repo/pdf-reader"
    assert output["name"] == "pdf-reader"
    assert output["description"] == "Read and extract text from PDF files"
    assert output["trust_tier"] == "official"
    assert output["license"] == "MIT"
    assert "install" in output
    assert "url" in output
    assert "content_hash" in output


def test_atlas_show_nonexistent_skill(test_repo):
    """Test 'atlas show' with non-existent skill."""
    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Try to show non-existent skill
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "show", "github.com/nonexistent/skill"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "not found" in result.stderr


def test_atlas_find_without_index(test_repo):
    """Test 'atlas find' without building index first."""
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "not found" in result.stderr
    assert "atlas index" in result.stderr


def test_json_schema_validation(test_repo):
    """Test that JSON output matches the schema."""
    import jsonschema

    # Build index first
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    # Get JSON output
    result = subprocess.run(
        ["python3", "-m", "tools.atlas", "find", "pdf", "--json"],
        cwd=test_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)

    # Load schema
    schema_path = Path(__file__).parent.parent / "index" / "schema" / "router-result.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    # Validate against schema
    jsonschema.validate(instance=output, schema=schema)


def test_atlas_index_creates_gitignored_db(test_repo):
    """Test that router.sqlite is created in build/ which should be gitignored."""
    # Build index
    subprocess.run(["python3", "-m", "tools.atlas", "index"], cwd=test_repo, check=True, capture_output=True)

    db_path = test_repo / "build" / "router.sqlite"
    assert db_path.exists()
    assert db_path.parent.name == "build"

    # Check that build/ is in .gitignore (in the actual repo)
    repo_root = Path(__file__).parent.parent
    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        assert "build/" in content
