# Curated Skills

This directory contains **high-quality Agent Skills** that have been vetted for quality, license-cleared for redistribution, and mirrored in full within this repository.

## What Belongs Here

Skills in `curated/` must meet **all** of these criteria:

1. **✅ License-cleared for redistribution**
   - MIT, Apache-2.0, BSD, CC-BY, or similar permissive license
   - License explicitly allows redistribution and modification
   - License file or header present in original source

2. **✅ Quality-vetted**
   - Well-documented with clear instructions
   - Follows SKILL.md format conventions
   - Tested and functional
   - Maintained (not abandoned)

3. **✅ Complete SKILL.md content**
   - Full skill body mirrored here (not just a pointer)
   - Content hash recorded in `index/skills.json`
   - Preserves original license attribution

4. **✅ No duplication**
   - Skill provides unique functionality
   - Or is a notably better implementation than existing alternatives

See [`docs/inclusion-criteria.md`](../docs/inclusion-criteria.md) for detailed requirements.

## Directory Structure

Each curated skill gets its own directory:

```
curated/
├── skill-id-1/
│   ├── SKILL.md          # The actual skill
│   ├── LICENSE           # Original license
│   └── metadata.json     # Additional metadata
├── skill-id-2/
│   ├── SKILL.md
│   └── LICENSE
...
```

## Submitting a Skill for Curation

1. **Verify license** — Ensure the skill's license allows redistribution
2. **Check quality** — Review against inclusion criteria
3. **Prepare submission:**
   - Create directory under `curated/` with kebab-case ID
   - Add SKILL.md (full content)
   - Add LICENSE file (from original)
   - Add metadata.json with additional details
4. **Update index** — Add entry to `index/skills.json` with:
   - All required fields
   - `layer: "curated"`
   - `content_hash` (SHA-256 of SKILL.md)
   - `curated_path` pointing to this directory
5. **Submit PR** with clear description of skill functionality and source

## Maintenance

Curated skills are actively maintained:
- Regular updates from upstream sources
- Content hash verification
- Link and reference checking
- Deprecation handling

---

**Note:** Skills in this directory are redistributed under their original licenses. Always check the specific skill's LICENSE file before use.
