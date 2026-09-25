# Router Implementation (S3-2)

## Overview

This document describes the implementation of `atlas find` and `atlas show` commands using SQLite FTS5 for skill search, as specified in PLAN.md §S3-2.

## Architecture

### Database Schema

The router uses SQLite with two main tables:

1. **`skills_fts`** (FTS5 virtual table)
   - `name`: Skill name
   - `desc`: Skill description
   - `kw_tags`: Keywords/tags (space-separated)
   - `body_head`: First 400 chars of body content
   - `skill_id`: Skill identifier (UNINDEXED)
   - Tokenizer: `porter unicode61`

2. **`skill_metadata`** (regular table)
   - Full skill records with install commands, trust tier, license, etc.
   - Indexed on `canonical_id` for deduplication

### BM25 Field Weighting

The FTS5 search uses field-weighted BM25 scoring:
- `name`: weight 3.0 (highest priority)
- `desc`: weight 2.0
- `kw_tags`: weight 2.0
- `body_head`: weight 1.0

Query: `bm25(skills_fts, 3.0, 2.0, 2.0, 1.0)`

### Ranking Algorithm

1. **Get top 50 from BM25** - Initial retrieval with field-weighted scores
2. **Group by canonical_id** - Deduplicate alternative implementations
3. **Select canonical skill** - Prefer skill where `skill_id == canonical_id`
4. **Downrank black-hole skills** - Multiply score by 0.3 for overly generic skills
5. **Apply trust/security bonuses** - Very small adjustments (0.1-0.2)
6. **Sort by final score** - Return top k results
7. **Abstain if score < τ** - Return `abstained: true` if confidence is too low

### Abstain Threshold

Current threshold: `0.1` (TODO: calibrate in S3-4 with evaluation set)

Black-hole patterns (overly broad skills):
- `general.?purpose`
- `any task`
- `all.?purpose`
- `do anything`
- `generic`

## Commands

### `atlas index`

Builds `build/router.sqlite` from `index/skills.jsonl`.

```bash
atlas index
```

- Skips inactive skills (`status != "active"`)
- Skips malicious skills (`security.status == "malicious"`)
- Calculates `alternatives_count` for each skill
- Output: `build/router.sqlite` (gitignored)

### `atlas find`

Search for skills using FTS5 BM25 ranking.

```bash
atlas find "<query>" [-k 5] [--layer curated] [--license permissive] [--min-trust official] [--json]
```

**Options:**
- `-k`: Number of results (default: 5)
- `--layer`: Filter by layer (`curated` or `source`)
- `--license`: Filter by license (`permissive` = allow-list licenses)
- `--min-trust`: Minimum trust tier (`official`, `community`, `unreviewed`)
- `--json`: Output as JSON

**Output (--json):**
```json
{
  "query": "pdf documents",
  "abstained": false,
  "results": [
    {
      "id": "github.com/example/skills/pdf",
      "name": "pdf",
      "description": "Extract text from PDF documents",
      "install": { "npx": "...", "gh": null, "claude_plugin": null },
      "url": "https://github.com/example/skills/tree/main/pdf",
      "content_hash": "sha256:...",
      "trust_tier": "official",
      "license": "MIT",
      "security": "pass",
      "alternatives_count": 2,
      "why_matched": {
        "fields": ["name", "desc"],
        "terms": ["pdf", "documents"],
        "bm25_rank": 1
      },
      "score": 12.3
    }
  ],
  "note": "Load only if needed. Confirm with the user before installing any skill whose trust_tier is not official/curated or whose security is not pass."
}
```

### `atlas show`

Display details for a specific skill by ID.

```bash
atlas show <id> [--json]
```

**Example:**
```bash
atlas show github.com/example/skills/pdf
```

## Performance

### Latency Targets

- **p95 latency:** ≤100ms (requirement from PLAN §S3-2)
- **Measured p95:** ~0.86ms on 100-skill fixture corpus
- **`get_skill_by_id` p95:** ~0.19ms

The implementation significantly exceeds the latency requirement.

### Measurement Method

Performance tests use `time.perf_counter()` to measure:
- 20 iterations per query
- 5 different queries
- Overall p95 calculated across all iterations

See `tests/test_router_performance.py` for details.

## Schema Validation

JSON output is validated against `index/schema/router-result.schema.json` (JSON Schema 2020-12).

Tests ensure all output conforms to the schema using `jsonschema.validate()`.

## Filters Implementation

### Layer Filter

```sql
WHERE m.layer = ?
```

### License Filter (permissive)

Maps to allow-list from `policy/licenses.json`:
- MIT, MIT-0, 0BSD, BSD-2-Clause, BSD-3-Clause
- ISC, Apache-2.0, CC-BY-4.0, CC0-1.0
- Unlicense, Zlib

```sql
WHERE m.license IN (?, ?, ...)
```

### Trust Filter

Trust tier ordering: `official` > `community` > `aggregator-copy` > `unreviewed`

```sql
WHERE m.trust_tier IN (?)
```

For `--min-trust community`, includes both `official` and `community`.

## Canonical Deduplication

Skills with the same `canonical_id` are grouped together. The router:
1. Groups all skills by their `canonical_id`
2. Within each group, prefers the skill where `skill_id == canonical_id`
3. If no canonical skill exists, takes the highest-scoring alternative
4. Sets `alternatives_count` for each returned skill

This ensures users see the original/canonical skill, not duplicate copies.

## Testing

### Unit Tests (`tests/test_router.py`)

- Build database from fixture data
- Search with various queries and filters
- Canonical deduplication
- Black-hole skill downranking
- Abstain logic
- JSON serialization
- Schema validation

### Integration Tests (`tests/test_router_cli.py`)

- CLI commands (`atlas index`, `atlas find`, `atlas show`)
- Text and JSON output formats
- Filter combinations
- Error handling (missing database, nonexistent skills)
- JSON schema validation of CLI output

### Performance Tests (`tests/test_router_performance.py`)

- p95 latency measurement on 100-skill corpus
- Cold vs warm cache comparison
- `get_skill_by_id` latency
- Full index performance (skipped if not available)

## Future Work

### S3-4 Evaluation

- Build evaluation set with ≥300 queries
- Calibrate `ABSTAIN_THRESHOLD` using eval data
- Measure Recall@5, MRR@10, nDCG@10
- Adjust black-hole detection patterns
- Fine-tune field weights if needed

### S3-6 Hybrid Retrieval (Optional)

If BM25-only doesn't meet quality gates:
- Add dense retrieval with `BAAI/bge-small-en-v1.5`
- RRF fusion (k=60)
- Agent reranking mode

## Files

- `tools/atlas/router.py` - Core router implementation
- `tools/atlas/__main__.py` - CLI commands (index, find, show)
- `index/schema/router-result.schema.json` - JSON output schema
- `tests/test_router.py` - Unit tests
- `tests/test_router_cli.py` - Integration tests
- `tests/test_router_performance.py` - Performance tests
- `docs/router.md` - This file

## References

- PLAN.md §S3-2 - Router v1 (SQLite FTS5) requirements
- PLAN.md §3.4 - Data files and size thresholds
- research/2026-09-24/router-papers.md - Router design research
