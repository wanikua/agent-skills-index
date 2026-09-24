#!/usr/bin/env python3
"""Exact deduplication and canonical lineage for Skill Atlas."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def cluster_by_content_hash(skills: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Cluster skills by their content_hash.

    Args:
        skills: List of skill records

    Returns:
        Dict mapping content_hash to list of skills with that hash
    """
    clusters = defaultdict(list)
    for skill in skills:
        content_hash = skill.get("hashes", {}).get("content_hash")
        if content_hash:
            clusters[content_hash].append(skill)
    return dict(clusters)


def parse_iso_datetime(timestamp: str | None) -> datetime | None:
    """
    Parse ISO 8601 timestamp to datetime object.

    Args:
        timestamp: ISO 8601 timestamp string

    Returns:
        datetime object or None if parsing fails
    """
    if not timestamp:
        return None
    try:
        # Handle both with and without microseconds
        if "." in timestamp:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        return None


def select_canonical(cluster: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Select the canonical skill from a cluster of duplicates.

    Selection criteria (in order of priority):
    1. Official trust tier (vendor-published)
    2. Earliest first_seen timestamp
    3. Most referenced upstream (by checking if skill appears in other repos)
    4. Alphabetical by ID (for determinism)

    Args:
        cluster: List of skills with the same content_hash

    Returns:
        The canonical skill record
    """
    if len(cluster) == 1:
        return cluster[0]

    # Priority 1: official trust tier
    official_skills = [s for s in cluster if s.get("trust_tier") == "official"]
    if official_skills:
        if len(official_skills) == 1:
            return official_skills[0]
        # Multiple official sources, continue with tie-breaking
        cluster = official_skills

    # Priority 2: earliest first_seen
    skills_with_timestamps = []
    for skill in cluster:
        first_seen = parse_iso_datetime(skill.get("first_seen"))
        if first_seen:
            skills_with_timestamps.append((skill, first_seen))

    if skills_with_timestamps:
        # Sort by timestamp, then by ID for determinism
        skills_with_timestamps.sort(key=lambda x: (x[1], x[0]["id"]))
        earliest_timestamp = skills_with_timestamps[0][1]

        # Get all skills with the earliest timestamp
        earliest_skills = [s for s, ts in skills_with_timestamps if ts == earliest_timestamp]

        if len(earliest_skills) == 1:
            return earliest_skills[0]

        # Multiple skills with same earliest timestamp, continue
        cluster = earliest_skills

    # Priority 3: Most referenced upstream
    # For now, we use a simple heuristic: skills from community tier are likely
    # to be more original than aggregator copies
    community_skills = [s for s in cluster if s.get("trust_tier") == "community"]
    if community_skills:
        if len(community_skills) == 1:
            return community_skills[0]
        cluster = community_skills

    # Final tie-breaker: alphabetical by ID
    cluster_sorted = sorted(cluster, key=lambda s: s["id"])
    return cluster_sorted[0]


def apply_deduplication(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Apply exact deduplication to skill records.

    This function:
    1. Clusters skills by content_hash
    2. Selects canonical skill for each cluster
    3. Marks duplicates with duplicate_of pointing to canonical
    4. Updates trust_tier to aggregator-copy for tier 3 duplicates

    Args:
        skills: List of skill records

    Returns:
        Updated list of skill records with dedup metadata
    """
    logger.info("Clustering skills by content_hash...")
    clusters = cluster_by_content_hash(skills)

    logger.info(f"Found {len(clusters)} unique content hashes")

    # Count duplicates
    duplicate_count = sum(len(cluster) - 1 for cluster in clusters.values() if len(cluster) > 1)
    cluster_count = sum(1 for c in clusters.values() if len(c) > 1)
    logger.info(f"Found {duplicate_count} duplicate skills across {cluster_count} clusters")

    # Process each cluster
    for content_hash, cluster in clusters.items():
        if len(cluster) == 1:
            # No duplicates, mark as canonical
            skill = cluster[0]
            skill["dedup"]["canonical_id"] = skill["id"]
            continue

        # Select canonical
        canonical = select_canonical(cluster)
        canonical_id = canonical["id"]

        logger.debug(
            f"Cluster with {len(cluster)} skills: canonical={canonical_id}, trust_tier={canonical.get('trust_tier')}"
        )

        # Update all skills in cluster
        for skill in cluster:
            skill_id = skill["id"]

            if skill_id == canonical_id:
                # This is the canonical skill
                skill["dedup"]["canonical_id"] = skill_id
            else:
                # This is a duplicate
                skill["dedup"]["duplicate_of"] = canonical_id

                # If this is a tier 3 skill, mark it as aggregator-copy
                # Check trust_tier directly since we don't need source tier lookup
                if skill.get("trust_tier") in ["unreviewed", "aggregator-copy"]:
                    skill["trust_tier"] = "aggregator-copy"

                logger.debug(
                    f"  Duplicate: {skill_id} -> canonical {canonical_id} (trust_tier={skill.get('trust_tier')})"
                )

    return skills


def compute_canonical_count(skills: list[dict[str, Any]]) -> int:
    """
    Count the number of canonical (non-duplicate) skills.

    Args:
        skills: List of skill records with dedup metadata

    Returns:
        Count of canonical skills
    """
    canonical_count = 0
    for skill in skills:
        # A skill is canonical if it has no duplicate_of field
        if not skill.get("dedup", {}).get("duplicate_of"):
            canonical_count += 1

    return canonical_count
