# Skill Atlas Architecture

This document describes the technical architecture of Skill Atlas, the largest and most complete Agent Skills Index.

---

## Overview

Skill Atlas operates on a **two-layer + router** architecture designed to balance reliability, breadth, and intelligent discovery.

```
┌─────────────────────────────────────────────────────────────┐
│                      Skill Atlas                             │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │   Curated      │  │    Source      │  │   Router     │  │
│  │   Layer        │  │    Index       │  │   (Future)   │  │
│  │                │  │                │  │              │  │
│  │  Full Skills   │  │  Pointers +    │  │  Discovery   │  │
│  │  Mirrored      │  │  Metadata      │  │  Intelligence│  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                              │
│              ┌──────────────────────────┐                   │
│              │   Machine-Readable       │                   │
│              │   Index Files            │                   │
│              │   (skills.json,          │                   │
│              │    sources.json)         │                   │
│              └──────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Curated Skills Mirror

### Purpose
Provide **high-reliability**, license-cleared Agent Skills that are:
- Quality-vetted
- Fully mirrored in this repository
- Actively maintained
- Safe for agents to use without additional verification

### Storage
- Directory: `curated/`
- Structure: One subdirectory per skill
- Contents: Full SKILL.md + LICENSE + metadata

### Index Entry
```json
{
  "id": "skill-id",
  "layer": "curated",
  "curated_path": "curated/skill-id/SKILL.md",
  "content_hash": "sha256...",
  ...
}
```

### Maintenance
- **Upstream syncing:** Regular updates from source repositories
- **Integrity verification:** Content hash validation
- **Version tracking:** Semantic versioning of mirrored content
- **Deprecation handling:** Mark deprecated skills, provide alternatives

### Quality Gates
See [`inclusion-criteria.md`](inclusion-criteria.md) for full requirements:
- Valid SKILL.md format
- Redistribution-friendly license
- Quality and functional testing
- No duplicates (or clear improvement)

---

## Layer 2: Source Index

### Purpose
Provide **breadth and discovery** across the entire Agent Skills ecosystem:
- Catalog public skill repositories
- Track metadata without full mirroring
- Include experimental and community skills
- Enable exploration beyond curated set

### Storage
- Directory: `sources/` (minimal; mostly just pointers)
- Primary catalog: `index/sources.json`
- Contents: Repository URLs, patterns, metadata

### Index Entry
```json
{
  "id": "skill-id",
  "layer": "source",
  "source_repo": "https://github.com/...",
  "source_path": "path/to/SKILL.md",
  ...
}
```

### Discovery Pattern
Repositories can specify a glob pattern for automatic skill discovery:
```json
{
  "skill_pattern": "skills/**/SKILL.md"
}
```

Future tooling could crawl these patterns to expand the catalog.

### Maintenance
- **Link verification:** Check URLs are still accessible
- **Metadata updates:** Refresh descriptions, counts, tags
- **Pruning:** Remove dead links or abandoned repositories
- **Expansion:** Add newly discovered skill repositories

---

## Layer 3: Router (Future)

### Purpose
Provide **intelligent discovery** that helps agents:
- Query the right layer first (curated preferred)
- Fall back to source index when needed
- Search external sources as last resort
- Learn from successful discoveries

### Current State: v0 Stub
`router/SKILL.md` is a basic skill that teaches agents:
1. Query `index/skills.json` first
2. Prefer `layer: curated`
3. Use `sources/` for broader search
4. Report valuable discoveries back

### Future Enhancement
A more sophisticated router could:
- **Intelligent ranking:** Score skills by relevance, quality, popularity
- **Semantic search:** Embed skill descriptions for similarity matching
- **Usage analytics:** Track which skills are most used
- **Recommendation engine:** Suggest related or complementary skills
- **External federation:** Query other skill registries and aggregate results
- **Caching layer:** Cache frequently accessed external skills

---

## Index Files

### skills.json

**Location:** `index/skills.json`

**Purpose:** Machine-readable catalog of all skills (both curated and source)

**Schema:** See [`schema.md`](../index/schema.md)

**Key Fields:**
- `skills[]` — Array of all skill entries
- `total_count`, `curated_count`, `source_count` — Metadata counters
- `generated_at` — Freshness indicator
- `schema_version` — Format version

**Generation:**
- Currently manual (edit directly)
- Future: Automated generation from directory contents + source crawling

### sources.json

**Location:** `index/sources.json`

**Purpose:** Catalog of skill repositories and discovery patterns

**Schema:** See [`schema.md`](../index/schema.md)

**Key Fields:**
- `repositories[]` — Array of source repository entries
- `total_repositories` — Count
- `generated_at` — Freshness indicator

**Future Enhancement:**
- Automatic crawling of `skill_pattern` globs
- Repository health scoring
- Last-checked timestamps

---

## Data Flow

### Agent Discovery Flow

```
1. Agent receives task requiring a skill
        ↓
2. Agent reads AGENTS.md (if first visit)
        ↓
3. Agent queries index/skills.json
        ↓
4. Agent filters/searches for relevant skills
        ↓
5. Agent prefers layer: curated
        ↓
6. If curated match: Read from curated/skill-id/SKILL.md
        ↓
7. If source match: Fetch from source_repo + source_path
        ↓
8. If no match: Fall back to broader web search
        ↓
9. Agent uses skill to complete task
        ↓
10. (Optional) Agent reports discovery or feedback
```

### Curation Flow

```
1. New skill discovered or submitted
        ↓
2. Validate format (SKILL.md conventions)
        ↓
3. Check license (redistribution allowed?)
        ↓
4. Quality review (functional, documented, secure)
        ↓
5. Deduplication check (already exists?)
        ↓
6. Decision:
   ├─ Curated: Mirror to curated/, update skills.json
   └─ Source: Add pointer to sources.json
        ↓
7. Compute content_hash (if curated)
        ↓
8. Commit and merge PR
        ↓
9. Index now includes new skill
```

---

## Versioning and Updates

### Schema Versioning
- `schema_version` in index files follows semantic versioning
- Breaking changes require major version bump
- New optional fields require minor version bump
- See [`schema.md`](../index/schema.md) for details

### Skill Versioning
- Each skill tracks its own `version` field
- Curated skills sync versions from upstream
- Content hash changes indicate updates needed

### Repository Versioning
- Skill Atlas repo itself uses standard git tags
- Snapshot releases can bundle curated skills for offline use

---

## Performance Considerations

### Index Size
- `skills.json` should remain under ~10MB for fast loading
- If exceeds, consider:
  - Pagination (split into multiple files)
  - Summary index + detail files per skill
  - Compression

### Content Hashing
- SHA-256 for integrity and change detection
- Computed from normalized content (UTF-8, LF)
- Enables quick checks without full downloads

### Caching
- Index files are immutable at each commit SHA
- Agents can cache based on:
  - Git commit hash
  - `generated_at` timestamp
  - Content hash of individual skills

---

## Security and Trust

### Curated Layer
- **Manual review required** before inclusion
- License and author verification
- Functional testing when feasible
- No arbitrary code execution in SKILL.md itself

### Source Layer
- **Lower trust:** Pointers to external content
- Agents should:
  - Verify before using
  - Check license
  - Test in safe environment
  - Report issues

### Content Integrity
- Content hashes for curated skills
- Git commit signatures (future)
- Provenance tracking from source to curation

---

## Extensibility

### Plugin Architecture (Future)
- Skill Atlas could define "skill types" or "skill protocols"
- Standardize interfaces for common patterns
- Enable composition and chaining

### Federation (Future)
- Other registries could adopt compatible schema
- Cross-registry discovery
- Distributed but interoperable ecosystem

### Automation (Future)
- Automated source crawling
- PR automation for upstream updates
- CI/CD for validation and testing

---

## Technology Choices

### Current: Simple and Portable
- **JSON** for indexes (widely supported, machine-readable)
- **Markdown** for documentation (human-readable, git-friendly)
- **Git** for version control and provenance
- **SHA-256** for integrity

### Future Considerations
- **SQLite** for local querying
- **Graph database** for dependency and relationship tracking
- **Vector embeddings** for semantic search
- **Web API** for live querying without git clone

---

## Deployment and Distribution

### Current: Git Repository
- Clone or download from GitHub
- Index files at known paths
- No build step required

### Future Options
- **CDN hosting** of index files
- **npm/pip package** for programmatic access
- **Docker image** with pre-loaded index
- **Browser extension** for IDE integration

---

## Metrics and Analytics (Future)

Track:
- **Usage:** Which skills are most queried
- **Coverage:** Skill count over time
- **Quality:** Issue reports, update frequency
- **Community:** Contributors, PRs, stars

Goal: Understand ecosystem health and prioritize curation efforts.

---

## Roadmap

> **Superseded.** The executable roadmap now lives in [`PLAN.md`](PLAN.md), updated on 2026-09-24 from the landscape research in [`research/2026-09-24/`](research/2026-09-24/README.md). It changes several decisions below: location-based skill IDs, no required `version` field, per-skill license resolution, security gates before scale-out, and the router moved to `skills/skill-atlas/`. The list below is kept only for history.

### v0 (Current)
- ✅ Repository structure
- ✅ Index schema
- ✅ Documentation
- ✅ Empty but valid indexes

### v1 (Next)
- 🔲 Seed curated layer with ~10-20 high-quality skills
- 🔲 Add ~5-10 source repositories
- 🔲 Validation tooling (schema checks, link verification)
- 🔲 Contribution guidelines

### v2 (Future)
- 🔲 Automated source crawling
- 🔲 Semantic search capability
- 🔲 Web API for live queries
- 🔲 Community moderation tools

### v3+ (Vision)
- 🔲 Router with intelligent ranking
- 🔲 Federation with other registries
- 🔲 Usage analytics and recommendations
- 🔲 Skill composition and dependency management

---

## Contributing to Architecture

Proposals for architectural changes:
1. Open an issue describing the problem and proposed solution
2. Discuss trade-offs and alternatives
3. Update this document with the decision (even if "no change")
4. Implement if approved

Architecture decisions should prioritize:
1. **Agent usability** — Easy for agents to discover and use skills
2. **Maintainability** — Sustainable for human maintainers
3. **Extensibility** — Room to grow without breaking changes
4. **Simplicity** — Prefer simple solutions that work

---

For questions or suggestions, open an issue in the [agent-skills-index repository](https://github.com/wanikua/agent-skills-index).
