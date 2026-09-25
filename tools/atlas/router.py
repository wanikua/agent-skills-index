"""Router module - SQLite FTS5-based skill search (S3-2)."""

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SkillMatch:
    """A matched skill with ranking information."""

    id: str
    name: str
    description: str
    install: dict[str, str | None]
    url: str
    content_hash: str
    trust_tier: str
    license: str
    security: str
    alternatives_count: int
    why_matched: dict[str, Any]
    score: float


@dataclass
class SearchResult:
    """Search result with query and matches."""

    query: str
    abstained: bool
    results: list[SkillMatch]
    note: str = (
        "Load only if needed. Confirm with the user before installing any skill "
        "whose trust_tier is not official/curated or whose security is not pass."
    )


# TODO: Calibrate this threshold using S3-4 evaluation set
# For now, use a conservative value that will be updated after eval
# Note: Set lower for testing; in production, this should be calibrated
ABSTAIN_THRESHOLD = 0.1  # Very low threshold for now; will calibrate in S3-4


# Black-hole skills: overly broad skills that match too many queries
# These get downranked to avoid dominating results
BLACK_HOLE_PATTERNS = [
    r"\bgeneral.?purpose\b",
    r"\bany task\b",
    r"\ball.?purpose\b",
    r"\bdo anything\b",
    r"\bgeneric\b",
]


def is_black_hole_skill(description: str, name: str) -> bool:
    """Check if a skill is overly broad and should be downranked."""
    text = (description + " " + name).lower()
    for pattern in BLACK_HOLE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def build_router_db(skills_jsonl: Path, output_db: Path) -> int:
    """
    Build SQLite FTS5 database from skills.jsonl.

    Args:
        skills_jsonl: Path to skills.jsonl file
        output_db: Path to output router.sqlite file

    Returns:
        Number of skills indexed

    Schema:
        - FTS5 table with columns: name, desc, kw_tags, body_head
        - Metadata table with full skill records
        - Field-weighted BM25: bm25(t, 3.0, 2.0, 2.0, 1.0)
    """
    # Remove existing database
    if output_db.exists():
        output_db.unlink()

    # Connect and create schema
    conn = sqlite3.connect(output_db)
    conn.execute("PRAGMA journal_mode=WAL")

    # Create FTS5 table with tokenizer and field weights
    # Note: BM25 weights are applied at query time via bm25() function
    conn.execute("""
        CREATE VIRTUAL TABLE skills_fts USING fts5(
            name,
            desc,
            kw_tags,
            body_head,
            skill_id UNINDEXED,
            tokenize='porter unicode61'
        )
    """)

    # Create metadata table for full records
    conn.execute("""
        CREATE TABLE skill_metadata (
            skill_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            install_npx TEXT,
            install_gh TEXT,
            install_claude_plugin TEXT,
            url TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            trust_tier TEXT NOT NULL,
            license TEXT NOT NULL,
            security TEXT NOT NULL,
            alternatives_count INTEGER NOT NULL DEFAULT 0,
            canonical_id TEXT,
            layer TEXT NOT NULL
        )
    """)

    # Create index on canonical_id for deduplication
    conn.execute("CREATE INDEX idx_canonical ON skill_metadata(canonical_id)")

    # Load and index skills
    count = 0
    if not skills_jsonl.exists():
        conn.close()
        return 0

    with open(skills_jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            skill = json.loads(line)

            # Skip inactive or malicious skills
            if skill.get("status") != "active":
                continue
            if skill.get("security", {}).get("status") == "malicious":
                continue

            # Extract fields for FTS
            skill_id = skill["id"]
            name = skill.get("name", "")
            desc = skill.get("description", "")

            # Extract keywords (top tags)
            tags = skill.get("tags", [])
            kw_tags = " ".join(tags[:12]) if tags else ""

            # Extract body head (first 400 words from frontmatter or description)
            # For now, use description since we're in source index layer
            # When D5 is implemented, this will include body content for allowed licenses
            body_head = desc[:400] if desc else ""

            # Insert into FTS table
            conn.execute(
                """
                INSERT INTO skills_fts (name, desc, kw_tags, body_head, skill_id)
                VALUES (?, ?, ?, ?, ?)
            """,
                (name, desc, kw_tags, body_head, skill_id),
            )

            # Extract metadata
            install = skill.get("install", {})
            source = skill.get("source", {})
            url = source.get("url", "")
            hashes = skill.get("hashes", {})
            content_hash = hashes.get("content_hash", "")
            trust_tier = skill.get("trust_tier", "unreviewed")
            license_info = skill.get("license", {})
            license_spdx = license_info.get("spdx", "NOASSERTION")
            security_info = skill.get("security", {})
            security_status = security_info.get("status", "pending")

            # Calculate alternatives count (skills with same canonical_id)
            dedup = skill.get("dedup", {})
            canonical_id = dedup.get("canonical_id")
            alternatives_count = 0  # Will be updated in a second pass

            layer = skill.get("layer", "source")

            # Insert into metadata table
            conn.execute(
                """
                INSERT INTO skill_metadata
                (skill_id, name, description, install_npx, install_gh, install_claude_plugin,
                 url, content_hash, trust_tier, license, security, alternatives_count,
                 canonical_id, layer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    skill_id,
                    name,
                    desc,
                    install.get("npx"),
                    install.get("gh"),
                    install.get("claude_plugin"),
                    url,
                    content_hash,
                    trust_tier,
                    license_spdx,
                    security_status,
                    alternatives_count,
                    canonical_id,
                    layer,
                ),
            )

            count += 1

    # Update alternatives_count
    conn.execute("""
        UPDATE skill_metadata
        SET alternatives_count = (
            SELECT COUNT(*) - 1
            FROM skill_metadata m2
            WHERE m2.canonical_id = skill_metadata.canonical_id
              AND m2.canonical_id IS NOT NULL
        )
        WHERE canonical_id IS NOT NULL
    """)

    conn.commit()
    conn.close()

    return count


def search_skills(
    db_path: Path,
    query: str,
    k: int = 5,
    layer: str | None = None,
    license_filter: str | None = None,
    min_trust: str | None = None,
) -> SearchResult:
    """
    Search for skills using FTS5 with BM25 ranking.

    Args:
        db_path: Path to router.sqlite
        query: Search query string
        k: Number of results to return (default: 5)
        layer: Filter by layer ("curated" or "source")
        license_filter: Filter by license class ("permissive" maps to allow-list licenses)
        min_trust: Minimum trust tier ("official", "community", "unreviewed")

    Returns:
        SearchResult with ranked matches

    Ranking algorithm:
        1. Get BM25 top 50
        2. Deduplicate by canonical_id (keep highest scoring)
        3. Downrank black-hole skills
        4. Apply trust/security as tiny tie-breakers
        5. If top score < threshold, abstain
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Build WHERE clause for filters
    where_clauses = []
    params: list[Any] = []

    if layer:
        where_clauses.append("m.layer = ?")
        params.append(layer)

    if license_filter == "permissive":
        # Map to allow-list licenses (from policy/licenses.json)
        allow_list = [
            "MIT",
            "MIT-0",
            "0BSD",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "Apache-2.0",
            "CC-BY-4.0",
            "CC0-1.0",
            "Unlicense",
            "Zlib",
        ]
        placeholders = ",".join("?" * len(allow_list))
        where_clauses.append(f"m.license IN ({placeholders})")
        params.extend(allow_list)

    if min_trust:
        # Trust tier ordering: official > community > aggregator-copy > unreviewed
        trust_order = {"official": 4, "community": 3, "aggregator-copy": 2, "unreviewed": 1}
        min_value = trust_order.get(min_trust, 1)
        valid_tiers = [tier for tier, value in trust_order.items() if value >= min_value]
        placeholders = ",".join("?" * len(valid_tiers))
        where_clauses.append(f"m.trust_tier IN ({placeholders})")
        params.extend(valid_tiers)

    where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

    # Query with BM25 field weighting: name=3.0, desc=2.0, kw_tags=2.0, body_head=1.0
    # Get top 50 for post-processing
    # Note: FTS5 bm25() function requires the table name, not an alias
    sql = f"""
        SELECT
            f.skill_id,
            m.name,
            m.description,
            m.install_npx,
            m.install_gh,
            m.install_claude_plugin,
            m.url,
            m.content_hash,
            m.trust_tier,
            m.license,
            m.security,
            m.alternatives_count,
            m.canonical_id,
            bm25(skills_fts, 3.0, 2.0, 2.0, 1.0) as bm25_score
        FROM skills_fts f
        JOIN skill_metadata m ON f.skill_id = m.skill_id
        WHERE skills_fts MATCH ?{where_sql}
        ORDER BY bm25_score
        LIMIT 50
    """

    params.insert(0, query)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        return SearchResult(query=query, abstained=False, results=[])

    # Post-processing: dedup by canonical_id
    # Group by canonical_id and keep the best scoring within each group
    canonical_groups: dict[str, list[tuple[Any, float]]] = {}

    for row in rows:
        canonical_id = row["canonical_id"] if row["canonical_id"] else row["skill_id"]

        # Calculate adjusted score
        base_score = -row["bm25_score"]  # BM25 returns negative scores, invert

        # Downrank black-hole skills
        is_black_hole = is_black_hole_skill(row["description"], row["name"])
        if is_black_hole:
            base_score *= 0.3  # Strong downrank for overly generic skills

        # Trust tier bonus (very small)
        trust_bonus = {"official": 0.2, "community": 0.1, "aggregator-copy": 0.0, "unreviewed": 0.0}
        base_score += trust_bonus.get(row["trust_tier"], 0.0)

        # Security bonus (very small)
        security_bonus = {"pass": 0.1, "review": 0.0, "warn": -0.1, "malicious": -10.0}
        base_score += security_bonus.get(row["security"], 0.0)

        if canonical_id not in canonical_groups:
            canonical_groups[canonical_id] = []
        canonical_groups[canonical_id].append((row, base_score))

    # From each canonical group, pick the canonical skill if present, otherwise the highest scoring
    candidates = []
    for canonical_id, group in canonical_groups.items():
        # Sort group by score (descending)
        group.sort(key=lambda x: x[1], reverse=True)

        # Prefer the actual canonical skill (where skill_id == canonical_id)
        canonical_skill = None
        for row, score in group:
            if row["skill_id"] == canonical_id:
                canonical_skill = (row, score)
                break

        if canonical_skill:
            candidates.append(canonical_skill)
        else:
            # No canonical skill found, take the highest scoring
            candidates.append(group[0])

    # Sort by adjusted score
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Check if top score is below abstain threshold
    abstained = False
    if candidates and candidates[0][1] < ABSTAIN_THRESHOLD:
        abstained = True
        # Note: We still return results for debugging, but signal abstention
        # Production code may choose to return empty results instead

    # Build result matches (top k)
    matches = []
    for i, (row, score) in enumerate(candidates[:k]):
        # Determine which fields matched (simplified - would need query analysis)
        matched_fields = ["desc"]  # Always include desc as it has highest signal
        if query.lower() in row["name"].lower():
            matched_fields.insert(0, "name")

        match = SkillMatch(
            id=row["skill_id"],
            name=row["name"],
            description=row["description"],
            install={
                "npx": row["install_npx"],
                "gh": row["install_gh"],
                "claude_plugin": row["install_claude_plugin"],
            },
            url=row["url"],
            content_hash=row["content_hash"],
            trust_tier=row["trust_tier"],
            license=row["license"],
            security=row["security"],
            alternatives_count=row["alternatives_count"],
            why_matched={
                "fields": matched_fields,
                "terms": query.split()[:5],  # Simplified - would need proper query parsing
                "bm25_rank": i + 1,
            },
            score=round(score, 2),
        )
        matches.append(match)

    return SearchResult(query=query, abstained=abstained, results=matches)


def get_skill_by_id(db_path: Path, skill_id: str) -> dict[str, Any] | None:
    """
    Get a single skill by ID.

    Args:
        db_path: Path to router.sqlite
        skill_id: Skill identifier

    Returns:
        Skill record or None if not found
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT
            skill_id,
            name,
            description,
            install_npx,
            install_gh,
            install_claude_plugin,
            url,
            content_hash,
            trust_tier,
            license,
            security,
            alternatives_count,
            canonical_id,
            layer
        FROM skill_metadata
        WHERE skill_id = ?
    """,
        (skill_id,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "id": row["skill_id"],
        "name": row["name"],
        "description": row["description"],
        "install": {
            "npx": row["install_npx"],
            "gh": row["install_gh"],
            "claude_plugin": row["install_claude_plugin"],
        },
        "url": row["url"],
        "content_hash": row["content_hash"],
        "trust_tier": row["trust_tier"],
        "license": row["license"],
        "security": row["security"],
        "alternatives_count": row["alternatives_count"],
        "canonical_id": row["canonical_id"],
        "layer": row["layer"],
    }
