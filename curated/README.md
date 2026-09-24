# Curated Skills

This directory contains carefully vetted, mirrored Agent Skills from tier-1 sources. These skills meet strict quality, conformance, and security standards.

## Purpose

The `curated/` layer provides:

- **Offline access** to verified skills without external API calls
- **Immutable snapshots** tied to specific commits
- **License compliance** — all skills include their original LICENSE and proper attribution
- **Quality assurance** — all skills pass strict conformance and security checks

## Structure

```
curated/
  <owner>/
    <repo>/
      <skill-path>/
        SKILL.md
        LICENSE         ← verbatim upstream license
        ATTRIBUTION.md  ← provenance, commit SHA, modifications
        [scripts/]
        [references/]
        [other files as in upstream]
```

## Selection criteria

Skills in this directory are automatically selected and human-reviewed based on:

1. **Tier 1 source** (official vendor repositories)
2. **License class: `allow`** (MIT, Apache-2.0, BSD, CC0, etc.)
3. **Conformance: strict** (passes all spec checks)
4. **No duplicates** (not a copy of another skill)
5. **Text files only** (`.md`, `.py`, `.sh`, `.js`, `.ts`, `.json`, `.yaml`, `.txt`)
6. **Size limits** (each file ≤ 1 MB; SKILL.md ≤ 5,000 words)

## Curating skills

To add skills to this directory, use the `atlas curate` CLI:

```bash
# Auto-curate tier 1 skills that meet all criteria (dry run to see candidates)
atlas curate --auto-tier1 --dry-run

# Actually curate the skills (max 40 total, max 3 per source)
atlas curate --auto-tier1

# Curate a specific skill by ID
atlas curate --id "github.com/owner/repo/path/to/skill"
```

### Auto-curation process

The `--auto-tier1` command:
1. Scans `index/skills.jsonl` for skills meeting all criteria
2. Groups candidates by source
3. Selects up to 3 skills per tier-1 source (prioritizing clear descriptions, no scripts)
4. Limits total to 40 skills maximum
5. Creates mirrors with proper LICENSE and ATTRIBUTION

See [`docs/curation-guide.md`](../docs/curation-guide.md) for detailed instructions.

## Mirroring policy

- Upstream directories are copied **as-is**
- LICENSE files are taken **verbatim** from upstream (no SPDX template regeneration)
- `ATTRIBUTION.md` records the upstream URL, path, commit, copyright holder, and SPDX identifier
- If upstream included a NOTICE file, it's mirrored here and appended to `curated/NOTICE`

## Validation

All curated skills are validated by `atlas validate`, which checks:
- Each skill has a LICENSE file
- Each skill has an ATTRIBUTION.md file
- Content hashes match those in `index/skills.jsonl`
- All files are text files with whitelisted extensions
- File sizes are within limits
- SKILL.md word count is within limit

## Freshness

Mirrored skills are re-synced when upstream changes. If an upstream license becomes incompatible, we freeze the last compatible version and stop syncing.

---

For the full catalog, see [`index/skills.jsonl`](../index/skills.jsonl). Curated skills have a non-null `curated_path` field pointing to their location in this directory.
