# Skill Atlas Index Schema v2.0.0

> **Version:** 2.0.0  
> **Published:** 2026-09-24  
> **Breaking changes:** Identity model, hash requirements, no required `version` field

This document defines the schema for Skill Atlas index files. For machine-readable schemas, see:
- `index/schema/skill.schema.json` (JSON Schema 2020-12)
- `index/schema/source.schema.json`
- `index/schema/stats.schema.json`

---

## Overview

Skill Atlas maintains index files at two layers:

- **Source layer** (`index/skills.jsonl`, `index/sources.json`) — Complete catalog with pointers to upstream repositories
- **Curated layer** (`curated/`) — License-cleared, mirrored skills with full content

Both layers use the same skill record schema. The primary data file is `index/skills.jsonl` (one JSON object per line); `index/skills.json` provides a backward-compatible wrapper view.

---

## Core Principles (v2)

### 1. Location-Based Identity

**Skills are identified by their location, not their name.**

The primary key `id` is:
```
github.com/<owner>/<repo>/<skill-dir-path>
```

Where:
- `<owner>` and `<repo>` are **lowercase**
- `<skill-dir-path>` is the directory containing `SKILL.md`
- For SKILL.md in repository root: use `.` as the path

**Examples:**
- `github.com/anthropics/skills/skills/pdf`
- `github.com/cursor/my-skills/.` (root-level SKILL.md)

**Why:** Names are not unique. A skill's identity is its position in the source tree.

### 2. Cryptographic Hashes

Every skill record includes **three hashes** (both layers):

- **`skill_md_sha256`** — SHA-256 of raw SKILL.md bytes
- **`content_hash`** — SHA-256 of normalized content (format: `sha256:<hex>`)
- **`folder_sha256`** — SHA-256 of entire skill directory

**Normalization for `content_hash`:**
1. Remove BOM
2. Unicode NFC normalization
3. Convert CRLF to LF
4. Remove trailing whitespace from each line
5. Ensure single newline at EOF
6. Parse and re-serialize frontmatter with sorted keys
7. Remove provenance keys (`metadata.github-*`, `local-path`, `mintlify-proj`)

### 3. Commit SHA, Not Branch Names

All source references use **40-character commit SHA**, never branch names or tags.

### 4. No Required `version` Field

The spec does not define a `version` field. Use `declared_version` (from `metadata.version` in frontmatter) when present, but it is optional and not validated.

---

## Data Files

| File | Format | Purpose |
|------|--------|---------|
| `index/skills.jsonl` | JSONL (1 record/line, sorted by `id`) | Canonical skill catalog |
| `index/skills.json` | JSON wrapper object | Backward-compatible view |
| `index/sources.json` | JSON array | Source repository catalog |
| `index/stats.json` | JSON object | Index statistics (source of truth for README) |
| `index/changes.jsonl` | JSONL (append-only) | Change log |

**Size thresholds:**
- `skills.jsonl` > 50 MB → shard to `index/skills/<sha1-prefix>.jsonl`
- `skills.json` > 10 MB → include only curated + tier 1, add `"complete_catalog"` pointer

---

## Skill Record Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Location-based primary key (see §1) |
| `name` | string | Skill name from frontmatter (1-64 chars) |
| `description` | string | Skill description from frontmatter (1-1024 chars) |
| `layer` | enum | `"source"` or `"curated"` |
| `source` | object | Source metadata (see below) |
| `hashes` | object | Three hashes (see §2) |
| `frontmatter` | object | Parsed frontmatter |
| `conformance` | object | Spec validation results |
| `license` | object | License metadata |
| `trust_tier` | enum | `"official"`, `"community"`, `"aggregator-copy"`, or `"unreviewed"` |
| `status` | enum | `"active"`, `"removed"`, `"quarantined"`, or `"dangling"` |
| `first_seen` | string | ISO 8601 timestamp (UTC) |
| `last_seen` | string | ISO 8601 timestamp (UTC) |
| `last_changed` | string | ISO 8601 timestamp (UTC) |

### Source Object

```json
{
  "host": "github.com",
  "repo": "anthropics/skills",
  "path": "skills/pdf",
  "ref": "main",
  "commit": "abc123...",
  "blob_sha": "def456...",
  "url": "https://github.com/anthropics/skills/tree/abc123.../skills/pdf",
  "source_id": "anthropic-skills"
}
```

### Hashes Object

```json
{
  "skill_md_sha256": "e3b0c442...",
  "content_hash": "sha256:9f86d081...",
  "folder_sha256": "7f83b165..."
}
```

### License Object

```json
{
  "declared": "MIT",
  "spdx": "MIT",
  "evidence": "frontmatter",
  "file": "skills/pdf/LICENSE",
  "class": "allow"
}
```

**License classes:**
- `allow` — Freely redistributable (MIT, Apache-2.0, BSD, CC0, etc.)
- `conditional` — Copyleft or share-alike (MPL-2.0, LGPL, CC-BY-SA)
- `deny` — Non-redistributable (GPL, AGPL, Proprietary, CC-BY-NC, etc.)
- `unknown` — Could not determine

### Conformance Object

```json
{
  "strict": true,
  "lenient": true,
  "errors": [],
  "dialects": ["claude-code"]
}
```

**Strict mode requires:**
- `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` and equals directory name
- `description` 1-1024 characters
- No unknown top-level frontmatter keys

**Lenient mode:**
- Attempts to fix common errors (unquoted colons, etc.)
- Unknown keys moved to `extensions`
- Vendor extensions trigger dialect detection

### Trust Tier

Determined by source characteristics:

- `official` — Source owner_type is `vendor`
- `community` — Tier 2 sources
- `aggregator-copy` — Tier 3 sources with content_hash matching other repositories
- `unreviewed` — Everything else

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `declared_version` | string\|null | From `metadata.version` (not validated) |
| `packaging` | array | Detected formats: `"bare"`, `"claude-plugin"`, `"cursor-plugin"`, etc. |
| `install` | object | Installation commands (`npx`, `gh`, `claude_plugin`) |
| `tags` | array | Searchable keywords |
| `signals` | object | External verifiable signals (e.g., `repo_stars`) |
| `registry_ids` | object | IDs in external registries |
| `security` | object | Security scan results |
| `quality` | object | Quality lint results |
| `dedup` | object | Deduplication cluster info |
| `curated_path` | string\|null | Path in `curated/` if applicable |

---

## Source Record Schema

Sources are repositories that contain skills.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique source identifier (kebab-case) |
| `url` | string | Repository URL |
| `owner_type` | enum | `"vendor"`, `"community"`, or `"aggregator"` |
| `tier` | integer | 1 (official), 2 (community), or 3 (aggregator) |
| `status` | enum | `"active"`, `"missing"`, `"archived"`, or `"suspended"` |
| `added_at` | string | ISO 8601 timestamp (UTC) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `include_patterns` | array | Glob patterns for included paths |
| `exclude_patterns` | array | Glob patterns for excluded paths |
| `policy` | string | Special handling policy |
| `last_crawled_commit` | string\|null | Last crawled commit SHA |
| `last_crawled_at` | string\|null | ISO 8601 timestamp |
| `verified` | boolean | Manually verified |
| `notes` | string\|null | Internal notes |

---

## Stats Record Schema

`index/stats.json` is the **single source of truth** for numbers in README and other documentation.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version (e.g., "2.0.0") |
| `generated_at` | string | ISO 8601 timestamp (UTC) |
| `index_commit` | string | Git commit SHA of index data |
| `total_skills` | integer | Total skill count |
| `canonical_skills` | integer | Non-duplicate skill count |
| `repositories` | integer | Source repository count |
| `curated_skills` | integer | Curated layer skill count |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `by_license_class` | object | Skills grouped by license class |
| `by_trust_tier` | object | Skills grouped by trust tier |
| `spec_strict_valid_pct` | number | Percentage passing strict validation |
| `tier1_freshness_p50_hours` | number\|null | Median freshness (tier 1 sources) |

---

## Example Records

### Skill Record (Minimal)

```json
{
  "id": "github.com/anthropics/skills/skills/pdf",
  "name": "pdf",
  "description": "Extract and analyze content from PDF documents",
  "layer": "source",
  "source": {
    "host": "github.com",
    "repo": "anthropics/skills",
    "path": "skills/pdf",
    "ref": "main",
    "commit": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
    "blob_sha": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0a1",
    "url": "https://github.com/anthropics/skills/tree/a1b2c3d4.../skills/pdf",
    "source_id": "anthropic-skills"
  },
  "hashes": {
    "skill_md_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "content_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "folder_sha256": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
  },
  "frontmatter": {
    "license": "Proprietary. See LICENSE.txt",
    "compatibility": null,
    "allowed_tools": null,
    "metadata": {},
    "extensions": {}
  },
  "conformance": {
    "strict": true,
    "lenient": true,
    "errors": [],
    "dialects": ["claude-code"]
  },
  "license": {
    "declared": "Proprietary. See LICENSE.txt",
    "spdx": "LicenseRef-Proprietary",
    "evidence": "frontmatter",
    "file": "skills/pdf/LICENSE.txt",
    "class": "deny"
  },
  "trust_tier": "official",
  "status": "active",
  "first_seen": "2026-09-24T00:00:00Z",
  "last_seen": "2026-09-24T08:00:00Z",
  "last_changed": "2026-09-24T08:00:00Z"
}
```

### Source Record

```json
{
  "id": "anthropic-skills",
  "url": "https://github.com/anthropics/skills",
  "owner_type": "vendor",
  "tier": 1,
  "include_patterns": ["skills/*/SKILL.md"],
  "exclude_patterns": [],
  "status": "active",
  "added_at": "2026-09-24T00:00:00Z",
  "last_crawled_commit": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "last_crawled_at": "2026-09-24T08:00:00Z",
  "verified": true,
  "notes": null
}
```

### Stats Record

```json
{
  "schema_version": "2.0.0",
  "generated_at": "2026-09-24T08:00:00Z",
  "index_commit": "5e5f91b",
  "total_skills": 0,
  "canonical_skills": 0,
  "repositories": 0,
  "curated_skills": 0,
  "by_license_class": {
    "allow": 0,
    "conditional": 0,
    "deny": 0,
    "unknown": 0
  },
  "by_trust_tier": {
    "official": 0,
    "community": 0,
    "aggregator-copy": 0,
    "unreviewed": 0
  },
  "spec_strict_valid_pct": 0.0,
  "tier1_freshness_p50_hours": null
}
```

---

## Migration from v1 to v2

### Breaking Changes

1. **Identity model change**
   - **v1:** `id` was a kebab-case identifier derived from name
   - **v2:** `id` is location-based: `github.com/<owner>/<repo>/<path>`
   - **Migration:** Rebuild IDs from `source_repo` + `source_path`

2. **Required hashes**
   - **v1:** `content_hash` only on curated layer
   - **v2:** Three hashes required on all layers
   - **Migration:** Compute `skill_md_sha256`, `content_hash`, `folder_sha256` for all records

3. **No required `version`**
   - **v1:** `version` was a required field
   - **v2:** Use `declared_version` (optional, from frontmatter metadata only)
   - **Migration:** Move `version` to `declared_version`, allow null

4. **Commit SHA required**
   - **v1:** `source_repo` was a URL, version implicit
   - **v2:** `source.commit` must be a 40-character SHA
   - **Migration:** Resolve current HEAD or fetch commit history

5. **License object structure**
   - **v1:** `license` was a string (SPDX identifier)
   - **v2:** `license` is an object with `declared`, `spdx`, `evidence`, `class`
   - **Migration:** Parse license declarations per skill, not per repository

### New Fields in v2

- `source` (object) replaces `source_repo` + `source_path`
- `hashes` (object) with three hash types
- `frontmatter` (object) with parsed and extension fields
- `conformance` (object) with strict/lenient validation
- `license.evidence` and `license.class`
- `trust_tier` (replaces inferred tier)
- `security`, `quality`, `dedup` (new metadata)
- `first_seen`, `last_seen`, `last_changed` (replaces single `updated_at`)

### Removed Fields

- `author` — Not in spec; use `source.repo` owner or frontmatter metadata
- `curated_count` / `source_count` in skills.json root — Use `stats.json`
- `tags` is now optional (not required)
- `permissions`, `dependencies`, `language` — Move to extensions if needed

### Data File Changes

- **v1:** Single `skills.json` file
- **v2:** Primary file is `skills.jsonl` (one record per line); `skills.json` is a wrapper

---

## Validation

Use `atlas validate` to check index files against schemas:

```bash
atlas validate              # Validate all index files
atlas validate --schema     # JSON Schema validation only
atlas validate --wording    # Wording lint only
```

Schema files use JSON Schema 2020-12 and are located in `index/schema/`.

---

## Determinism

Index files are **deterministic**: given the same input, repeated builds produce identical output (byte-for-byte).

**Requirements:**
- JSON keys are sorted
- `generated_at` only updates when content changes
- No random values or timestamps-for-the-sake-of-timestamps
- Stable sort order for arrays (typically by `id`)

**File formats:**
- `.json` files: 2-space indent, `ensure_ascii=False`, trailing newline
- `.jsonl` files: compact format (no indent), one record per line, trailing newline

---

## Version History

### 2.0.0 (2026-09-24)
- **Breaking:** Location-based identity (`id` format change)
- **Breaking:** Required hashes on all layers
- **Breaking:** `version` removed, use `declared_version`
- **Breaking:** Commit SHA required in source metadata
- **Breaking:** License as object, not string
- Added: `source` object (replaces separate fields)
- Added: `frontmatter`, `conformance`, `trust_tier`
- Added: `security`, `quality`, `dedup` metadata
- Changed: Three timestamps (`first_seen`, `last_seen`, `last_changed`)
- Data file: `skills.jsonl` is now canonical

### 1.0.0 (2026-09-24)
- Initial schema definition
- Support for curated and source layers
- Basic skill and repository metadata

---

## Extending the Schema

When adding new fields:

1. Update `schema_version` following semantic versioning:
   - **Major:** Breaking changes (remove required fields, change types, change ID format)
   - **Minor:** New optional fields, new enum values
   - **Patch:** Documentation clarifications only

2. Mark new fields as optional initially
3. Document migration path for existing entries
4. Update JSON Schema files in `index/schema/`
5. Update this document
6. Add validation tests

---

## See Also

- `docs/PLAN.md` §S1-1 — Schema v2 implementation plan
- `docs/PLAN.md` §3.3 — Identity and hash specifications
- `docs/PLAN.md` §3.4 — Data file formats and thresholds
- `index/schema/*.schema.json` — Machine-readable schemas
- `docs/architecture.md` — Overall system design
