# Curation Guide

This document describes how to curate skills into the `curated/` directory.

## Overview

The `curated/` layer provides high-quality, vetted skills that meet strict criteria for license compatibility, conformance, and security. Skills are mirrored from tier-1 sources and include proper attribution.

## Prerequisites

Before curating skills, ensure:

1. The index has been built with `atlas build` (requires crawled data from `atlas crawl`)
2. Skills have been validated with `atlas validate`
3. License information has been parsed for all skills
4. Conformance checks have been run

## Curation Criteria

A skill must meet ALL of the following criteria to be eligible for curation:

### 1. Trust Tier
- Must be from a **tier 1** (official) source
- `trust_tier` field must equal `"official"`

### 2. License
- License must be in the **allow** class
- Allowed licenses: MIT, MIT-0, 0BSD, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0, CC-BY-4.0, CC0-1.0, Unlicense, Zlib
- See `policy/licenses.json` for the complete list

### 3. Conformance
- Must pass **strict** conformance validation
- `conformance.strict` must be `true`
- No critical spec violations

### 4. Uniqueness
- Must not be a duplicate of another skill
- `dedup.duplicate_of` must be `null`

### 5. File Constraints
- Only text files with whitelisted extensions: `.md`, `.py`, `.sh`, `.js`, `.ts`, `.json`, `.yaml`, `.yml`, `.txt`
- Common files without extensions are allowed: LICENSE, NOTICE, README, AUTHORS, CONTRIBUTORS, COPYING, ATTRIBUTION
- Each file must be ≤ 1 MB
- SKILL.md must be ≤ 5,000 words

## Using the Curate Command

### Auto-curate tier 1 skills

The recommended way to populate `curated/` is with the `--auto-tier1` flag:

```bash
# Dry run to see candidates
atlas curate --auto-tier1 --dry-run

# Actually curate (max 40 total, max 3 per source)
atlas curate --auto-tier1

# Customize limits
atlas curate --auto-tier1 --max-total 30 --max-per-source 2
```

The auto-curation process:
1. Filters skills by all criteria
2. Groups by source repository
3. Selects up to `--max-per-source` skills per tier-1 source (default: 3)
4. Limits total to `--max-total` (default: 40)
5. Prioritizes skills with clear descriptions and no scripts directory

### Curate a specific skill

To curate a single skill by its ID:

```bash
atlas curate --id "github.com/owner/repo/path/to/skill"
```

The command will:
1. Find the skill in the index
2. Validate it meets curation criteria
3. Mirror the skill directory to `curated/<owner>/<repo>/<path>/`
4. Copy the LICENSE verbatim
5. Generate ATTRIBUTION.md with provenance information

## Directory Structure

Curated skills are organized as:

```
curated/
  <owner>/          ← GitHub organization or user
    <repo>/         ← Repository name
      <skill-path>/ ← Path to skill within repo
        SKILL.md
        LICENSE
        ATTRIBUTION.md
        [other files from upstream]
```

For example:
```
curated/
  anthropics/
    skills/
      skills/
        pdf/
          SKILL.md
          LICENSE
          ATTRIBUTION.md
```

## Mirroring Policy

When mirroring a skill:

1. **Copy as-is**: The entire skill directory is copied without modifications
2. **LICENSE verbatim**: Use the upstream LICENSE file exactly as written (never regenerate from SPDX templates)
3. **NOTICE handling**: If the upstream has a NOTICE file:
   - Copy it to the skill directory
   - Append it to `curated/NOTICE` (the aggregate NOTICE file)
4. **ATTRIBUTION.md**: Generate attribution with:
   - Upstream repository URL
   - Path within repository
   - Commit SHA
   - Copyright holder
   - SPDX license identifier
   - Modifications note (typically "none" or "UTF-8/LF normalization only")

## Validation

After curation, run `atlas validate` to ensure:
- Every curated skill has LICENSE and ATTRIBUTION.md
- Content hashes match the index
- All files meet size and extension requirements

## First Batch Guidelines

For the initial curated batch (task S1-7):

- **Target**: 20-40 skills only
- **Maximum per source**: 3 skills
- **Preferred skills**:
  - Clear, descriptive descriptions (≥40 characters)
  - No scripts directory
  - Simple, focused functionality
  
**Do NOT include**:
- Any tier-3 content
- Skills from anthropics/skills with docx/pdf/pptx/xlsx extensions
- Figma or Remotion related skills
- Modified upstream content

## Post-Curation

After curating skills:

1. Run validation: `atlas validate`
2. Commit changes with a descriptive message
3. Open a PR for CODEOWNERS review
4. The PR must be approved by repository owners before merging

## Future Enhancements

After S2 (security scanning) is complete:
- Add security check requirement: `security.status == "pass"`
- Implement automated rescanning on upstream changes
- Add downgrade/freeze on license changes
