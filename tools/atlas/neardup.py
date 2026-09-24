#!/usr/bin/env python3
"""Near-duplicate detection using MinHash LSH for Skill Atlas (S2-3)."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datasketch import MinHash

try:
    from datasketch import MinHash as _MinHash
    from datasketch import MinHashLSH
    from rapidfuzz import fuzz

    NEARDUP_AVAILABLE = True
    MinHash = _MinHash
except ImportError:
    NEARDUP_AVAILABLE = False
    MinHash = None  # type: ignore
    MinHashLSH = None  # type: ignore
    fuzz = None  # type: ignore

logger = logging.getLogger(__name__)

# Parameters calibrated on eval/dedup-pairs.jsonl (S2-8)
#
# Achieved metrics with these settings:
# - Precision: ~0.86
# - Recall: ~0.25
# - F1: ~0.38
#
# Note: Many eval "near-duplicates" are subjective (e.g., Next.js vs React,
# Keras vs TensorFlow) and semantically distinct. Edit-distance metrics cannot
# reliably distinguish framework relationships from true paraphrases without
# semantic understanding (embeddings), which PLAN.md explicitly prohibits.
#
# These parameters prioritize precision to minimize false positives on production data.
NUM_PERM = 128
LSH_THRESHOLD = 0.55  # LSH candidate threshold
NEAR_DUP_SIMILARITY = 0.77  # Optimized for precision/recall balance
MIRROR_SIMILARITY = 0.92  # For exact/near-exact duplicates
MIN_WORDS_FOR_MINHASH = 20  # Use MinHash for skills with 20+ words


def extract_body_text(content: str) -> str:
    """
    Extract body text from SKILL.md content (excluding frontmatter).

    Args:
        content: Raw SKILL.md content

    Returns:
        Body text without frontmatter
    """
    # Remove frontmatter if present
    if content.startswith("---\n"):
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1]

    return content


def tokenize_ngrams(text: str, n: int = 5) -> list[str]:
    """
    Tokenize text into word-level n-grams.

    Args:
        text: Input text
        n: N-gram size (default: 5)

    Returns:
        List of n-gram strings
    """
    # Normalize whitespace and convert to lowercase
    text = re.sub(r"\s+", " ", text.lower())

    # Split into words (keeping only alphanumeric and basic punctuation)
    words = re.findall(r"\w+", text)

    # Generate n-grams
    if len(words) < n:
        # For very short texts, return the whole sequence as one gram
        return [" ".join(words)] if words else []

    ngrams = []
    for i in range(len(words) - n + 1):
        ngram = " ".join(words[i : i + n])
        ngrams.append(ngram)

    return ngrams


def count_words(text: str) -> int:
    """Count words in text."""
    words = re.findall(r"\w+", text)
    return len(words)


def compute_minhash(text: str, num_perm: int = NUM_PERM) -> MinHash | None:
    """
    Compute MinHash for a text.

    Args:
        text: Input text
        num_perm: Number of permutations

    Returns:
        MinHash object or None if text is too short
    """
    if not NEARDUP_AVAILABLE:
        return None

    # Check word count
    word_count = count_words(text)
    if word_count < MIN_WORDS_FOR_MINHASH:
        return None

    # Generate 5-grams
    ngrams = tokenize_ngrams(text, n=5)

    if not ngrams:
        return None

    # Create MinHash
    m = MinHash(num_perm=num_perm)
    for ngram in ngrams:
        m.update(ngram.encode("utf-8"))

    return m


def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute text similarity using rapidfuzz.

    Uses both ratio and token_sort_ratio and takes the maximum,
    to handle both exact copies and paraphrased text.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0.0 to 1.0)
    """
    if not NEARDUP_AVAILABLE:
        return 0.0

    # Use both metrics and take the max
    # ratio: good for exact/near-exact copies
    # token_sort_ratio: good for reordered/paraphrased text
    ratio_sim = fuzz.ratio(text1, text2) / 100.0
    token_sim = fuzz.token_sort_ratio(text1, text2) / 100.0

    return max(ratio_sim, token_sim)


def find_near_duplicates(
    skills: list[dict[str, Any]],
    num_perm: int = NUM_PERM,
    lsh_threshold: float = LSH_THRESHOLD,
    near_dup_threshold: float = NEAR_DUP_SIMILARITY,
    mirror_threshold: float = MIRROR_SIMILARITY,
) -> dict[str, dict[str, Any]]:
    """
    Find near-duplicate skills using MinHash LSH.

    Args:
        skills: List of skill records
        num_perm: Number of MinHash permutations
        lsh_threshold: LSH similarity threshold for candidates
        near_dup_threshold: Similarity threshold for near_duplicate_of
        mirror_threshold: Similarity threshold for mirror_of

    Returns:
        Dict mapping skill ID to near-duplicate metadata
    """
    if not NEARDUP_AVAILABLE:
        logger.warning("MinHash deduplication not available (datasketch/rapidfuzz not installed)")
        return {}

    logger.info(f"Finding near-duplicates for {len(skills)} skills...")
    logger.info(
        f"Parameters: num_perm={num_perm}, lsh_threshold={lsh_threshold}, "
        f"near_dup={near_dup_threshold}, mirror={mirror_threshold}"
    )

    # Build LSH index
    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)

    # Store MinHash objects and body texts
    minhashes = {}
    body_texts = {}
    short_texts = {}  # Skills too short for MinHash (exact match only)

    for skill in skills:
        skill_id = skill["id"]

        # Skip skills that are already marked as exact duplicates
        if skill.get("dedup", {}).get("duplicate_of"):
            continue

        # Extract body text
        content = skill.get("_raw_content", "")
        if not content:
            logger.warning(f"No content for skill {skill_id}, skipping near-dup check")
            continue

        body_text = extract_body_text(content)
        body_texts[skill_id] = body_text

        # Compute MinHash
        mh = compute_minhash(body_text, num_perm=num_perm)

        if mh is not None:
            minhashes[skill_id] = mh
            lsh.insert(skill_id, mh)
        else:
            # Too short for MinHash - store for exact matching
            word_count = count_words(body_text)
            if word_count > 0:
                short_texts[skill_id] = body_text

    logger.info(f"Built LSH index with {len(minhashes)} skills ({len(short_texts)} too short for MinHash)")

    # Find candidate pairs from LSH
    near_dup_results = {}
    candidate_pairs = set()

    for skill_id, mh in minhashes.items():
        candidates = lsh.query(mh)
        for candidate_id in candidates:
            if candidate_id != skill_id:
                # Store pairs in canonical order to avoid duplicates
                pair = tuple(sorted([skill_id, candidate_id]))
                candidate_pairs.add(pair)

    logger.info(f"Found {len(candidate_pairs)} candidate pairs from LSH")

    # Verify candidates with edit similarity
    verified_near_dups = []
    verified_mirrors = []

    for skill_id_a, skill_id_b in candidate_pairs:
        text_a = body_texts[skill_id_a]
        text_b = body_texts[skill_id_b]

        similarity = compute_text_similarity(text_a, text_b)

        if similarity >= mirror_threshold:
            verified_mirrors.append((skill_id_a, skill_id_b, similarity))
        elif similarity >= near_dup_threshold:
            verified_near_dups.append((skill_id_a, skill_id_b, similarity))

    logger.info(f"Verified: {len(verified_mirrors)} mirrors, {len(verified_near_dups)} near-duplicates")

    # Check short texts with similarity-based matching
    short_matches = []
    short_ids = list(short_texts.keys())
    for i, id_a in enumerate(short_ids):
        for id_b in short_ids[i + 1 :]:
            text_a = short_texts[id_a]
            text_b = short_texts[id_b]

            similarity = compute_text_similarity(text_a, text_b)

            if similarity >= mirror_threshold:
                short_matches.append((id_a, id_b, similarity, "mirror"))
            elif similarity >= near_dup_threshold:
                short_matches.append((id_a, id_b, similarity, "near"))

    if short_matches:
        logger.info(f"Found {len(short_matches)} matches in short texts")
        for id_a, id_b, similarity, match_type in short_matches:
            if match_type == "mirror":
                verified_mirrors.append((id_a, id_b, similarity))
            else:
                verified_near_dups.append((id_a, id_b, similarity))

    # Build clusters using union-find to handle transitive relationships
    # This ensures that if A=B and B=C, then A, B, C are all in the same cluster
    parent = {}

    def find(x):
        """Find root of x with path compression."""
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        """Union two sets."""
        root_x = find(x)
        root_y = find(y)
        if root_x != root_y:
            parent[root_x] = root_y

    # Union all mirror pairs
    for id_a, id_b, _ in verified_mirrors:
        union(id_a, id_b)

    # Union all near-dup pairs
    for id_a, id_b, _ in verified_near_dups:
        union(id_a, id_b)

    # Build clusters
    clusters = defaultdict(list)
    all_skill_ids = set(body_texts.keys())

    for skill_id in all_skill_ids:
        root = find(skill_id)
        clusters[root].append(skill_id)

    logger.info(f"Found {len([c for c in clusters.values() if len(c) > 1])} duplicate clusters")

    # For each cluster, select canonical and mark relationship type
    near_dup_results = {}

    for root, cluster_members in clusters.items():
        if len(cluster_members) == 1:
            # No duplicates in this cluster
            continue

        # Get skill objects for cluster members
        cluster_skills = [next(s for s in skills if s["id"] == sid) for sid in cluster_members]

        # Select canonical
        canonical = _select_canonical_from_list(cluster_skills)
        canonical_id = canonical["id"]

        # Determine relationship type for each non-canonical skill
        for skill_id in cluster_members:
            if skill_id == canonical_id:
                continue

            # Check if this skill has a direct mirror relationship with canonical
            is_mirror = False
            for id_a, id_b, _ in verified_mirrors:
                if (id_a == skill_id and id_b == canonical_id) or (id_b == skill_id and id_a == canonical_id):
                    is_mirror = True
                    break

            # If not a direct mirror, check via similarity
            if not is_mirror and skill_id in body_texts and canonical_id in body_texts:
                sim = compute_text_similarity(body_texts[skill_id], body_texts[canonical_id])
                is_mirror = sim >= mirror_threshold

            if is_mirror:
                near_dup_results[skill_id] = {"mirror_of": canonical_id}
            else:
                near_dup_results[skill_id] = {"near_duplicate_of": canonical_id}

    logger.info(f"Total near-duplicate relationships: {len(near_dup_results)}")

    return near_dup_results


def _select_canonical_from_list(cluster: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Select canonical skill from a cluster of duplicates.

    Same logic as _select_canonical_pair but handles lists.

    Args:
        cluster: List of skills in the cluster

    Returns:
        The canonical skill
    """
    if len(cluster) == 1:
        return cluster[0]

    # Priority 1: official trust tier
    official_skills = [s for s in cluster if s.get("trust_tier") == "official"]
    if official_skills:
        if len(official_skills) == 1:
            return official_skills[0]
        cluster = official_skills

    # Priority 2: earliest first_seen
    from tools.atlas.dedup import parse_iso_datetime

    skills_with_timestamps = []
    for skill in cluster:
        first_seen = parse_iso_datetime(skill.get("first_seen"))
        if first_seen:
            skills_with_timestamps.append((skill, first_seen))

    if skills_with_timestamps:
        skills_with_timestamps.sort(key=lambda x: (x[1], x[0]["id"]))
        earliest_timestamp = skills_with_timestamps[0][1]
        earliest_skills = [s for s, ts in skills_with_timestamps if ts == earliest_timestamp]

        if len(earliest_skills) == 1:
            return earliest_skills[0]
        cluster = earliest_skills

    # Priority 3: community tier
    community_skills = [s for s in cluster if s.get("trust_tier") == "community"]
    if community_skills:
        if len(community_skills) == 1:
            return community_skills[0]
        cluster = community_skills

    # Final tie-breaker: alphabetical by ID
    cluster_sorted = sorted(cluster, key=lambda s: s["id"])
    return cluster_sorted[0]


def _select_canonical_pair(skill_a: dict[str, Any], skill_b: dict[str, Any]) -> dict[str, Any]:
    """Select canonical from a pair (delegates to _select_canonical_from_list)."""
    return _select_canonical_from_list([skill_a, skill_b])


def apply_near_deduplication(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Apply near-duplicate detection to skills and update dedup fields.

    This function should be called after exact deduplication (S2-2).

    Args:
        skills: List of skill records (with dedup.duplicate_of already populated)

    Returns:
        Updated list of skill records
    """
    if not NEARDUP_AVAILABLE:
        logger.warning("Near-duplicate detection skipped (datasketch/rapidfuzz not installed)")
        return skills

    # Find near-duplicates
    near_dup_results = find_near_duplicates(skills)

    # Apply results to skills
    for skill in skills:
        skill_id = skill["id"]

        if skill_id in near_dup_results:
            result = near_dup_results[skill_id]

            if "mirror_of" in result:
                skill["dedup"]["mirror_of"] = result["mirror_of"]
            elif "near_duplicate_of" in result:
                skill["dedup"]["near_duplicate_of"] = result["near_duplicate_of"]

    return skills
