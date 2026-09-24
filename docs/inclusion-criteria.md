# Inclusion Criteria

This document defines the requirements for Agent Skills to be included in Skill Atlas.

---

## Curated Layer Requirements

Skills in `curated/` must meet **all** of the following criteria:

### 1. Valid SKILL.md Format

- **✅ Proper structure:**
  - Clear skill name and description
  - Well-documented instructions for agents
  - Examples or usage patterns
  - Prerequisites or dependencies listed

- **✅ Format conventions:**
  - Markdown formatting
  - Named `SKILL.md` (case-sensitive)
  - UTF-8 encoding
  - LF line endings (Unix-style)

- **✅ Agent-readable:**
  - Clear, imperative instructions
  - No ambiguous language
  - Testable or verifiable outcomes
  - Appropriate context and constraints

### 2. License Allowing Redistribution

One of the following licenses (or compatible):

**Preferred:**
- MIT
- Apache-2.0
- BSD-2-Clause
- BSD-3-Clause
- CC-BY-4.0

**Acceptable:**
- ISC
- MPL-2.0
- LGPL (with appropriate notices)

**Not acceptable for curated/:**
- GPL (strong copyleft; creates compliance burden)
- Proprietary or closed-source
- "All Rights Reserved"
- No license (legally no redistribution rights)
- Custom licenses (must be reviewed case-by-case)

**License must:**
- Be present in the source repository (LICENSE file or header)
- Explicitly allow redistribution and modification
- Permit commercial use (preferred)

### 3. Quality Bar

- **✅ Functional:**
  - Skill has been tested and works
  - Instructions are accurate and complete
  - No broken links or references

- **✅ Maintained:**
  - Source repository shows recent activity
  - Issues and PRs are addressed
  - Not abandoned or deprecated

- **✅ Documented:**
  - Purpose and use case are clear
  - Examples or demonstrations provided
  - Edge cases or limitations noted

- **✅ Secure:**
  - No obvious security vulnerabilities
  - Doesn't encourage unsafe practices
  - Credentials and secrets handled properly

### 4. Deduplication Rules

Before adding to `curated/`:

- **✅ Search existing catalog** for similar functionality
- **✅ Evaluate vs. alternatives:**
  - Is this a clear improvement? (faster, more reliable, better docs)
  - Does it provide unique functionality?
  - Is it from a more authoritative source?

- **Prefer:**
  - Official skills over community rewrites
  - Actively maintained over abandoned
  - Better documented over sparse
  - Simpler implementation over complex (when equivalent)

- **Reject duplicates unless:**
  - Significantly better quality
  - Solves limitations of existing skill
  - From authoritative/official source

### 5. Content Requirements

- **✅ Attribution:**
  - Original author credited
  - Source repository linked
  - License preserved

- **✅ Completeness:**
  - Full SKILL.md content (not excerpt)
  - Associated assets if needed
  - Metadata fields populated

- **✅ Integrity:**
  - Content hash (SHA-256) computed
  - No modifications to skill content (except format normalization)
  - Versioned appropriately

---

## Source Layer Requirements

Skills/repositories in the source index (`sources/`) have **lower** requirements:

### 1. Pointer-Only Metadata

- **✅ Public URL** to repository or SKILL.md file
- **✅ Basic metadata:**
  - Name and description
  - Author
  - Tags

### 2. License Tracking (No Redistribution Requirement)

- License tracked in metadata (if available)
- **No requirement** that license allow redistribution
- Include even GPL, proprietary, or unknown licenses
- Clearly mark license in `index/sources.json`

### 3. Quality (Preferred, Not Required)

- Source index can include:
  - Experimental skills
  - Unvetted community contributions
  - Abandoned but still-useful repositories
  - Skills with no clear license

- **Agents should:**
  - Prefer curated over source layer
  - Check license before using source skills
  - Verify quality independently

### 4. Deduplication (Relaxed)

- Multiple sources providing similar functionality are OK
- Agents can choose based on needs
- Breadth is a feature of the source layer

---

## Special Cases

### Community Contributions

- **Welcome!** Community skills can be curated if they meet all criteria
- Initial curations will likely focus on official/well-known repositories
- Small improvements or fixes are valuable contributions

### Multi-File Skills

If a skill requires additional files beyond SKILL.md:
- Include all necessary files in `curated/skill-id/`
- Document file structure in metadata
- Ensure all files are license-compatible

### Translations

Skills in non-English languages:
- Welcome in both curated and source layers
- Mark with `language` field in metadata
- Prefer to have English description/summary for discoverability

### Deprecated Skills

If a curated skill becomes deprecated:
1. Mark as deprecated in metadata
2. Note replacement (if available)
3. Keep in archive for backward compatibility
4. Eventually remove after transition period

### Upstream License Changes

If a curated skill's upstream license becomes incompatible:
1. Snapshot final compatible version
2. Mark as "frozen" or "snapshot" in metadata
3. Stop syncing updates
4. Note situation in skill documentation

---

## Review Process

### For Curated Submissions

1. **Automated checks:**
   - License verification
   - Format validation
   - Link checking
   - Duplicate detection

2. **Manual review:**
   - Quality assessment
   - Functional testing (if feasible)
   - Documentation review
   - Security spot-check

3. **Approval criteria:**
   - All automated checks pass
   - At least one maintainer approval
   - No unresolved concerns

### For Source Submissions

1. **Minimal automated checks:**
   - URL accessibility
   - Basic metadata completeness

2. **Quick manual review:**
   - Not spam or malicious
   - Genuinely skill-related

3. **Low bar for approval** — breadth is the goal

---

## Questions?

- **Open an issue** for clarification on specific cases
- **Submit a draft PR** to discuss a potential inclusion
- **Tag maintainers** for edge-case evaluation

We aim to be inclusive while maintaining high quality in the curated layer and comprehensive coverage in the source layer.
