# Source Index

This directory contains **pointers and metadata** for Agent Skill repositories across the internet. Unlike `curated/`, this layer does **not** mirror full skill bodies.

## What Belongs Here

The source index tracks:

1. **🔗 Public skill repositories**
   - GitHub, GitLab, or other public git hosting
   - Direct links to SKILL.md files or skill directories
   - Author and maintainer information

2. **📋 Metadata only**
   - Repository URL and structure
   - Skill discovery patterns (e.g., glob patterns)
   - Tags, categories, and descriptions
   - **Not full skill content**

3. **📊 Broader ecosystem catalog**
   - May include repositories with various licenses
   - May include experimental or unvetted skills
   - **Use with appropriate caution**

## Directory Structure

This directory primarily serves as context for the `index/sources.json` catalog. Optional per-repository metadata files:

```
sources/
├── README.md              # This file
└── [optional metadata files for specific source repos]
```

The canonical source catalog is **`index/sources.json`** at the repository root.

## Adding a Source Repository

To add a new source repository to the index:

1. **Verify it's public** — URL must be publicly accessible
2. **Identify skill locations** — Note paths or patterns for SKILL.md files
3. **Update `index/sources.json`** with:
   - Unique repository ID
   - Full repository URL
   - Description and author
   - Skill count (if known)
   - Discovery pattern (e.g., `skills/**/SKILL.md`)
   - Tags for categorization
4. **Submit PR** with clear description

## Source vs. Curated

| Aspect | Source Index | Curated Mirror |
|--------|--------------|----------------|
| **Content** | Pointers only | Full SKILL.md mirrored |
| **License** | Any (tracked) | Redistribution-friendly only |
| **Quality** | Varies | Vetted and maintained |
| **Reliability** | Depends on upstream | Stable within this repo |
| **Breadth** | Broad ecosystem | Selected high-quality |

**Recommendation for agents:** Prefer `curated/` for reliability. Use `sources/` when specific functionality is needed that's not yet curated.

## Maintenance

The source index is:
- **Updated daily at 03:17 UTC** via automated refresh workflow
- Updated regularly with new repository discoveries
- Verified for link integrity
- Pruned when repositories become unavailable
- Enhanced with metadata as the ecosystem evolves

---

**Contribute:** Know a valuable skill repository? Submit a PR adding it to `index/sources.json`!
