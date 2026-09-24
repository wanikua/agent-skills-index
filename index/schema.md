# Skill Atlas Index Schema

This document defines the schema for Skill Atlas index files.

## Overview

Skill Atlas maintains two primary index files:
- **`skills.json`** — Catalog of individual Agent Skills
- **`sources.json`** — Catalog of skill repositories and sources

Both use semantic versioning (`schema_version`) to track changes.

---

## skills.json Schema

### Root Object

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Semantic version of this schema (e.g., "1.0.0") |
| `generated_at` | string | ISO 8601 timestamp of index generation |
| `description` | string | Human-readable description |
| `total_count` | integer | Total number of skills in catalog |
| `curated_count` | integer | Number of curated layer skills |
| `source_count` | integer | Number of source layer pointers |
| `skills` | array | Array of Skill objects (see below) |

### Skill Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique identifier (kebab-case, e.g., "notion-search") |
| `name` | string | ✅ | Display name of the skill |
| `description` | string | ✅ | What the skill does (1-2 sentences) |
| `author` | string | ✅ | Creator or maintainer name/organization |
| `license` | string | ✅ | SPDX license identifier (e.g., "MIT", "Apache-2.0") |
| `version` | string | ✅ | Semantic version of the skill (e.g., "1.2.3") |
| `layer` | string | ✅ | Either `curated` or `source` |
| `source_repo` | string | ✅ | Full repository URL (e.g., GitHub, GitLab) |
| `source_path` | string | ✅ | Path to SKILL.md within repository |
| `content_hash` | string | ⚪ | SHA-256 hash of skill content (curated only) |
| `updated_at` | string | ✅ | ISO 8601 timestamp of last update |
| `tags` | array[string] | ✅ | Searchable categories/keywords |
| `permissions` | array[string] | ⚪ | Required permissions or capabilities |
| `dependencies` | array[string] | ⚪ | IDs of other skills this depends on |
| `language` | string | ⚪ | Primary language ("en", "zh", "ja", etc.) |
| `curated_path` | string | ⚪ | Relative path in this repo (curated layer only) |

### Example Skill Entry

```json
{
  "id": "notion-search",
  "name": "Notion Search",
  "description": "Search across Notion workspace using the Notion MCP server.",
  "author": "Cursor Team",
  "license": "MIT",
  "version": "1.0.0",
  "layer": "curated",
  "source_repo": "https://github.com/cursor/skills",
  "source_path": "skills/notion/search/SKILL.md",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "updated_at": "2026-09-24T08:00:00Z",
  "tags": ["notion", "search", "mcp", "database"],
  "permissions": ["notion:read"],
  "curated_path": "curated/notion-search/SKILL.md",
  "language": "en"
}
```

---

## sources.json Schema

### Root Object

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Semantic version of this schema |
| `generated_at` | string | ISO 8601 timestamp of index generation |
| `description` | string | Human-readable description |
| `total_repositories` | integer | Total number of source repositories |
| `repositories` | array | Array of Repository objects (see below) |

### Repository Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique repository identifier (kebab-case) |
| `url` | string | ✅ | Full repository URL |
| `name` | string | ✅ | Repository display name |
| `description` | string | ✅ | What this repository contains |
| `author` | string | ✅ | Repository owner/organization |
| `license` | string | ⚪ | Repository license (if uniform across skills) |
| `skill_count` | integer | ✅ | Number of skills in this repository |
| `skill_paths` | array[string] | ⚪ | Paths to individual SKILL.md files |
| `skill_pattern` | string | ⚪ | Glob pattern for discovering skills (e.g., "skills/**/SKILL.md") |
| `added_at` | string | ✅ | ISO 8601 timestamp when added to index |
| `updated_at` | string | ✅ | ISO 8601 timestamp of last update |
| `tags` | array[string] | ✅ | Repository-level categories |
| `verified` | boolean | ✅ | Whether repository has been manually verified |

### Example Repository Entry

```json
{
  "id": "cursor-official-skills",
  "url": "https://github.com/cursor/agent-skills",
  "name": "Cursor Official Skills",
  "description": "Official Agent Skills from the Cursor team",
  "author": "Cursor",
  "license": "MIT",
  "skill_count": 15,
  "skill_pattern": "skills/**/SKILL.md",
  "added_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-24T08:00:00Z",
  "tags": ["official", "cursor", "verified"],
  "verified": true
}
```

---

## Field Conventions

### IDs
- Use **kebab-case** (lowercase with hyphens)
- Must be unique within their scope
- Descriptive and memorable (e.g., "github-pr-review", not "skill-001")

### Timestamps
- Always **ISO 8601 format** (`YYYY-MM-DDTHH:mm:ssZ`)
- UTC timezone

### Tags
- Lowercase
- Single words or hyphenated phrases
- Common tags: `search`, `api`, `database`, `github`, `notion`, `testing`, `mcp`, `cli`

### Licenses
- Use **SPDX identifiers** when possible
- Common: `MIT`, `Apache-2.0`, `GPL-3.0`, `BSD-3-Clause`
- Use `Proprietary` for closed-source
- Use `Unknown` if unclear (but investigate before adding)

### Layers
- **`curated`** — Full skill body mirrored in this repo, license-cleared
- **`source`** — Pointer only; fetch from source_repo + source_path

### Content Hashes
- **SHA-256** hex string
- Computed from canonical SKILL.md content (UTF-8, LF line endings)
- Used for integrity verification and change detection

---

## Version History

### 1.0.0 (2026-09-24)
- Initial schema definition
- Support for curated and source layers
- Basic skill and repository metadata

---

## Extending the Schema

When adding new fields:
1. Update `schema_version` following semantic versioning
2. Mark new fields as optional initially (⚪ in docs)
3. Document migration path for existing entries
4. Update this document with the change

Backward compatibility:
- **Major version:** Breaking changes (removing required fields, changing types)
- **Minor version:** New optional fields, new enum values
- **Patch version:** Documentation clarifications, no schema changes
