"""Hash computation for skills following section 3.3 of PLAN.md.

This module implements:
1. skill_md_sha256: Raw SHA-256 of the SKILL.md file
2. content_hash: Normalized SHA-256 with provenance key stripping
3. folder_sha256: Directory hash compatible with vercel-labs/skills
"""

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

PROVENANCE_KEYS = {
    "local-path",
    "mintlify-proj",
}


def compute_skill_md_sha256(content: bytes) -> str:
    """Compute raw SHA-256 of the SKILL.md file bytes.

    Args:
        content: Raw bytes of the SKILL.md file

    Returns:
        Hexadecimal SHA-256 hash string
    """
    return hashlib.sha256(content).hexdigest()


def _strip_bom(content: bytes) -> bytes:
    """Remove BOM (Byte Order Mark) from content."""
    if content.startswith(b"\xef\xbb\xbf"):
        return content[3:]
    if content.startswith(b"\xff\xfe"):
        return content[2:]
    if content.startswith(b"\xfe\xff"):
        return content[2:]
    return content


def _normalize_unicode(text: str) -> str:
    """Apply Unicode NFC normalization."""
    return unicodedata.normalize("NFC", text)


def _normalize_line_endings(text: str) -> str:
    """Convert CRLF to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_trailing_whitespace(text: str) -> str:
    """Remove trailing whitespace from each line."""
    lines = text.split("\n")
    return "\n".join(line.rstrip() for line in lines)


def _ensure_single_trailing_newline(text: str) -> str:
    """Ensure the file ends with exactly one newline."""
    text = text.rstrip("\n")
    return text + "\n"


def _extract_frontmatter(text: str) -> Tuple[Dict, str]:
    """Extract and parse YAML frontmatter from text.

    Returns:
        Tuple of (frontmatter_dict, body_without_frontmatter)
    """
    if not text.startswith("---\n"):
        return {}, text

    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}, text

    frontmatter_text = match.group(1)
    body = text[match.end() :]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return {}, text
        return frontmatter, body
    except yaml.YAMLError:
        return {}, text


def _strip_provenance_keys(frontmatter: Dict) -> Dict:
    """Remove provenance keys from frontmatter.

    Removes:
    - metadata.github-* keys
    - local-path
    - mintlify-proj
    """
    cleaned = {}

    for key, value in frontmatter.items():
        if key in PROVENANCE_KEYS:
            continue

        if key == "metadata" and isinstance(value, dict):
            cleaned_metadata = {k: v for k, v in value.items() if not k.startswith("github-")}
            if cleaned_metadata:
                cleaned["metadata"] = cleaned_metadata
        else:
            cleaned[key] = value

    return cleaned


def _serialize_frontmatter(frontmatter: Dict) -> str:
    """Serialize frontmatter dict to YAML with sorted keys."""
    if not frontmatter:
        return ""

    yaml_content = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
        width=120,
    )
    return f"---\n{yaml_content}---\n"


def compute_content_hash(content: bytes) -> str:
    """Compute normalized content hash following PLAN.md §3.3.

    Normalization steps:
    1. Remove BOM
    2. Unicode NFC normalization
    3. CRLF → LF
    4. Strip trailing whitespace from each line
    5. Ensure single trailing newline
    6. Strip provenance keys from frontmatter and re-serialize sorted

    Args:
        content: Raw bytes of the SKILL.md file

    Returns:
        SHA-256 hash with 'sha256:' prefix
    """
    content = _strip_bom(content)

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")

    text = _normalize_unicode(text)
    text = _normalize_line_endings(text)
    text = _strip_trailing_whitespace(text)
    text = _ensure_single_trailing_newline(text)

    frontmatter, body = _extract_frontmatter(text)

    if frontmatter:
        cleaned_frontmatter = _strip_provenance_keys(frontmatter)
        normalized_text = _serialize_frontmatter(cleaned_frontmatter) + body
    else:
        normalized_text = text

    hash_value = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"sha256:{hash_value}"


def compute_folder_sha256(skill_dir: Path) -> str:
    """Compute directory hash compatible with vercel-labs/skills.

    Algorithm:
    - Collect all files in the directory (recursively)
    - Sort by relative path
    - For each file: hash(relpath + file_bytes)
    - Hash the concatenation of all individual hashes

    This matches the vercel-labs/skills computedHash algorithm.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Hexadecimal SHA-256 hash of the folder
    """
    if not skill_dir.is_dir():
        raise ValueError(f"Path is not a directory: {skill_dir}")

    files: List[Tuple[str, bytes]] = []

    for file_path in sorted(skill_dir.rglob("*")):
        if not file_path.is_file():
            continue

        if file_path.is_symlink():
            continue

        rel_path = file_path.relative_to(skill_dir).as_posix()

        try:
            file_bytes = file_path.read_bytes()
        except (OSError, PermissionError):
            continue

        files.append((rel_path, file_bytes))

    hasher = hashlib.sha256()

    for rel_path, file_bytes in files:
        entry_hasher = hashlib.sha256()
        entry_hasher.update(rel_path.encode("utf-8"))
        entry_hasher.update(file_bytes)
        hasher.update(entry_hasher.digest())

    return hasher.hexdigest()
