#!/usr/bin/env python3
"""Generate router-lite shards for zero-install Agent discovery."""

import json
import logging
import re
from collections import Counter, defaultdict
from math import log
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Maximum sizes (in bytes)
MAX_CURATED_SIZE = 100 * 1024  # 100 KB
MAX_OFFICIAL_SIZE = 100 * 1024  # 100 KB
MAX_COMMUNITY_SHARD_SIZE = 1 * 1024 * 1024  # 1 MB

# Keyword extraction parameters
MAX_KEYWORDS = 12
MIN_KEYWORD_LENGTH = 3
MAX_KEYWORD_LENGTH = 30

# High-frequency boilerplate terms to filter out (English stopwords + domain-specific)
STOPWORDS = {
    "the",
    "be",
    "to",
    "of",
    "and",
    "a",
    "in",
    "that",
    "have",
    "i",
    "it",
    "for",
    "not",
    "on",
    "with",
    "he",
    "as",
    "you",
    "do",
    "at",
    "this",
    "but",
    "his",
    "by",
    "from",
    "they",
    "we",
    "say",
    "her",
    "she",
    "or",
    "an",
    "will",
    "my",
    "one",
    "all",
    "would",
    "there",
    "their",
    "what",
    "so",
    "up",
    "out",
    "if",
    "about",
    "who",
    "get",
    "which",
    "go",
    "me",
    "when",
    "make",
    "can",
    "like",
    "time",
    "no",
    "just",
    "him",
    "know",
    "take",
    "people",
    "into",
    "year",
    "your",
    "good",
    "some",
    "could",
    "them",
    "see",
    "other",
    "than",
    "then",
    "now",
    "look",
    "only",
    "come",
    "its",
    "over",
    "think",
    "also",
    "back",
    "after",
    "use",
    "two",
    "how",
    "our",
    "work",
    "first",
    "well",
    "way",
    "even",
    "new",
    "want",
    "because",
    "any",
    "these",
    "give",
    "day",
    "most",
    "us",
    # Domain-specific boilerplate
    "skill",
    "agent",
    "claude",
    "cursor",
    "plugin",
    "use",
    "when",
    "how",
    "can",
    "will",
    "using",
    "used",
    "uses",
    "allows",
    "provides",
    "enables",
    "helps",
    "make",
    "makes",
    "create",
    "creates",
    "get",
    "gets",
    "set",
    "sets",
}


def extract_keywords(
    name: str,
    description: str,
    body_head: str | None,
    titles: list[str] | None,
    idf_scores: dict[str, float] | None = None,
) -> list[str]:
    """
    Extract keywords from skill metadata using TF-IDF.

    Args:
        name: Skill name
        description: Skill description
        body_head: First 400 words of body (if allowed by license)
        titles: List of markdown titles from body (if body not allowed)
        idf_scores: Pre-computed IDF scores for corpus (if available)

    Returns:
        List of up to MAX_KEYWORDS keywords
    """
    # Collect text from all available sources
    text_parts = []

    # Name gets higher weight (we'll add it multiple times)
    if name:
        text_parts.extend([name.lower()] * 3)

    # Description gets medium weight
    if description:
        text_parts.extend([description.lower()] * 2)

    # Titles get medium weight
    if titles:
        for title in titles[:20]:  # Limit to first 20 titles
            text_parts.append(title.lower())

    # Body head gets standard weight
    if body_head:
        text_parts.append(body_head.lower())

    # Combine all text
    full_text = " ".join(text_parts)

    # Tokenize (simple word extraction)
    # Remove markdown formatting and special characters
    full_text = re.sub(r"[#*`_\[\]()]", " ", full_text)
    full_text = re.sub(r"https?://\S+", " ", full_text)  # Remove URLs

    # Extract words
    words = re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b", full_text)

    # Filter by length and stopwords
    words = [w for w in words if MIN_KEYWORD_LENGTH <= len(w) <= MAX_KEYWORD_LENGTH and w not in STOPWORDS]

    if not words:
        return []

    # Compute term frequencies
    tf = Counter(words)

    # Apply IDF if available, otherwise just use TF
    if idf_scores:
        # TF-IDF scoring
        scores = {}
        for term, freq in tf.items():
            idf = idf_scores.get(term, log(1000))  # Default IDF for unknown terms
            scores[term] = freq * idf
    else:
        # Just use TF if no IDF available
        scores = dict(tf)

    # Sort by score and take top keywords
    sorted_terms = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    keywords = [term for term, _score in sorted_terms[:MAX_KEYWORDS]]

    return keywords


def compute_idf_scores(skills: list[dict[str, Any]]) -> dict[str, float]:
    """
    Compute IDF scores across the corpus.

    Args:
        skills: List of skill records

    Returns:
        Dict mapping term to IDF score
    """

    # Count documents containing each term
    doc_freq = defaultdict(int)
    total_docs = 0

    for skill in skills:
        # Collect text
        text_parts = []
        if skill.get("name"):
            text_parts.append(skill["name"].lower())
        if skill.get("description"):
            text_parts.append(skill["description"].lower())

        full_text = " ".join(text_parts)
        full_text = re.sub(r"[#*`_\[\]()]", " ", full_text)
        full_text = re.sub(r"https?://\S+", " ", full_text)

        words = set(re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b", full_text))
        words = {w for w in words if MIN_KEYWORD_LENGTH <= len(w) <= MAX_KEYWORD_LENGTH and w not in STOPWORDS}

        for word in words:
            doc_freq[word] += 1

        total_docs += 1

    if total_docs == 0:
        return {}

    # Compute IDF: log(N / df)
    idf_scores = {}
    for term, df in doc_freq.items():
        idf_scores[term] = log(total_docs / df)

    return idf_scores


def extract_body_info(
    skill: dict[str, Any],
    body_content: str | None,
) -> tuple[str | None, list[str] | None]:
    """
    Extract body head or titles based on license class (⚠️D5).

    Args:
        skill: Skill record
        body_content: Full SKILL.md content if available

    Returns:
        (body_head, titles) - only one will be non-None based on license
    """
    license_class = skill.get("license", {}).get("class", "unknown")

    if not body_content:
        return None, None

    # Allow/conditional licenses: store first 400 words of body
    if license_class in ["allow", "conditional"]:
        # Extract body (skip frontmatter)
        lines = body_content.split("\n")
        in_frontmatter = False
        body_lines = []

        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    in_frontmatter = False
                    continue

            if not in_frontmatter:
                body_lines.append(line)

        body_text = "\n".join(body_lines)
        words = body_text.split()[:400]
        body_head = " ".join(words)

        return body_head, None

    # Other licenses: only store title list (≤20)
    else:
        titles = []
        lines = body_content.split("\n")

        for line in lines:
            if line.startswith("#"):
                # Extract title text
                title = re.sub(r"^#+\s*", "", line).strip()
                if title:
                    titles.append(title)

                if len(titles) >= 20:
                    break

        return None, titles


def create_router_lite_record(
    skill: dict[str, Any],
    keywords: list[str],
) -> dict[str, Any]:
    """
    Create a compact router-lite record with short keys.

    Format: {"id","n","d","kw","tier","lic","sec","install","url","h"}

    Args:
        skill: Full skill record
        keywords: Extracted keywords

    Returns:
        Compact record with short keys
    """
    # Truncate description to 200 chars
    desc = skill.get("description", "")
    if len(desc) > 200:
        desc = desc[:197] + "..."

    record = {
        "id": skill["id"],
        "n": skill.get("name", ""),
        "d": desc,
        "kw": keywords,
        "tier": skill.get("trust_tier", "unreviewed"),
        "lic": skill.get("license", {}).get("spdx", "NOASSERTION"),
        "sec": skill.get("security", {}).get("status", "pending"),
        "install": skill.get("install", {}),
        "url": skill.get("source", {}).get("url", ""),
        "h": skill.get("hashes", {}).get("content_hash", ""),
    }

    return record


def should_include_in_router_lite(skill: dict[str, Any]) -> bool:
    """
    Check if a skill should be included in router-lite.

    Filters:
    - Only canonical entries (dedup.canonical_id is null or equals id)
    - Exclude status != active
    - Exclude security.status == malicious

    Args:
        skill: Skill record

    Returns:
        True if should be included
    """
    # Check canonical
    dedup = skill.get("dedup", {})
    canonical_id = dedup.get("canonical_id")

    # If canonical_id is set and doesn't match id, this is not canonical
    if canonical_id and canonical_id != skill["id"]:
        return False

    # Check status
    if skill.get("status") != "active":
        return False

    # Check security
    security_status = skill.get("security", {}).get("status")
    if security_status == "malicious":
        return False

    return True


def generate_router_lite(
    skills: list[dict[str, Any]],
    output_dir: Path,
    body_content_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Generate router-lite shards from skills index.

    Creates:
    - curated.jsonl (≤100 KB)
    - official.jsonl (≤100 KB)
    - community-XX.jsonl (each ≤1 MB)

    Args:
        skills: List of skill records from skills.jsonl
        output_dir: Output directory for router-lite files
        body_content_map: Optional map of skill id to SKILL.md content

    Returns:
        Result dict with counts and file info
    """
    logger.info("Generating router-lite shards...")

    # Filter to canonical, active, non-malicious skills
    filtered_skills = [s for s in skills if should_include_in_router_lite(s)]
    logger.info(f"  Filtered {len(skills)} skills to {len(filtered_skills)} canonical/active/safe")

    if not filtered_skills:
        logger.warning("No skills to include in router-lite")
        return {
            "success": True,
            "total_skills": 0,
            "files_created": [],
        }

    # Compute IDF scores across corpus
    logger.info("  Computing IDF scores...")
    idf_scores = compute_idf_scores(filtered_skills)

    # Extract keywords and create router-lite records
    logger.info("  Extracting keywords and creating records...")
    router_lite_records = []

    for skill in filtered_skills:
        # Extract body info if available
        body_content = None
        if body_content_map:
            body_content = body_content_map.get(skill["id"])

        body_head, titles = extract_body_info(skill, body_content)

        # Extract keywords
        keywords = extract_keywords(
            skill.get("name", ""),
            skill.get("description", ""),
            body_head,
            titles,
            idf_scores,
        )

        # Create compact record
        record = create_router_lite_record(skill, keywords)
        router_lite_records.append(record)

    # Split into groups: curated, official, community
    curated_records = [r for r in router_lite_records if r["tier"] == "curated"]
    official_records = [r for r in router_lite_records if r["tier"] == "official" and r not in curated_records]
    community_records = [
        r
        for r in router_lite_records
        if r["tier"] in ["community", "unreviewed", "aggregator-copy"]
        and r not in curated_records
        and r not in official_records
    ]

    logger.info(
        f"  Split: {len(curated_records)} curated, {len(official_records)} official, {len(community_records)} community"
    )

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    # Write curated.jsonl
    if curated_records:
        curated_file = output_dir / "curated.jsonl"
        size = _write_shard(curated_records, curated_file, MAX_CURATED_SIZE, "curated")
        files_created.append({"file": "curated.jsonl", "records": len(curated_records), "size": size})

    # Write official.jsonl
    if official_records:
        official_file = output_dir / "official.jsonl"
        size = _write_shard(official_records, official_file, MAX_OFFICIAL_SIZE, "official")
        files_created.append({"file": "official.jsonl", "records": len(official_records), "size": size})

    # Write community-XX.jsonl shards
    if community_records:
        shard_num = 0
        current_shard = []
        current_size = 0

        for record in community_records:
            record_json = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            record_size = len(record_json.encode("utf-8"))

            # Check if adding this record would exceed limit
            if current_size + record_size > MAX_COMMUNITY_SHARD_SIZE and current_shard:
                # Write current shard
                shard_file = output_dir / f"community-{shard_num:02d}.jsonl"
                size = _write_shard(current_shard, shard_file, MAX_COMMUNITY_SHARD_SIZE, f"community-{shard_num:02d}")
                files_created.append(
                    {
                        "file": f"community-{shard_num:02d}.jsonl",
                        "records": len(current_shard),
                        "size": size,
                    }
                )

                # Start new shard
                shard_num += 1
                current_shard = []
                current_size = 0

            current_shard.append(record)
            current_size += record_size

        # Write final shard
        if current_shard:
            shard_file = output_dir / f"community-{shard_num:02d}.jsonl"
            size = _write_shard(current_shard, shard_file, MAX_COMMUNITY_SHARD_SIZE, f"community-{shard_num:02d}")
            files_created.append(
                {
                    "file": f"community-{shard_num:02d}.jsonl",
                    "records": len(current_shard),
                    "size": size,
                }
            )

    logger.info(f"✓ Generated {len(files_created)} router-lite shards")

    return {
        "success": True,
        "total_skills": len(router_lite_records),
        "curated": len(curated_records),
        "official": len(official_records),
        "community": len(community_records),
        "files_created": files_created,
    }


def _write_shard(
    records: list[dict[str, Any]],
    output_file: Path,
    max_size: int,
    shard_name: str,
) -> int:
    """
    Write a router-lite shard file.

    Args:
        records: Records to write
        output_file: Output file path
        max_size: Maximum size in bytes
        shard_name: Name for logging

    Returns:
        Actual size written in bytes
    """
    # Write records
    with open(output_file, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    # Check size
    actual_size = output_file.stat().st_size

    if actual_size > max_size:
        logger.warning(f"⚠️  {shard_name} shard size {actual_size:,} bytes exceeds limit {max_size:,} bytes")

    logger.info(f"  Wrote {output_file.name}: {len(records)} records, {actual_size:,} bytes")

    return actual_size
