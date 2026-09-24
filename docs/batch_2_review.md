# Batch 2 Backlog Review

This document lists the 14 repositories from `batch_2_backlog` (see `docs/research/2026-09-24/seed-batch-1.json`) that require human verification before they can be added to `index/sources.json` with `verified: true`.

## Purpose

Task S1-9 includes reviewing these repositories to determine if they should be added as sources in the next batch. This is a **discovery-only** task: repositories are NOT automatically added to `sources.json`. A human maintainer must verify each repository and mark it as `verified: true` before it enters the index.

## Discovery Status

The `atlas discover awesome` command found **3 out of 14** batch_2_backlog repositories in the aggregator READMEs:

- ✅ cloudflare/security-audit-skill
- ✅ coreyhaines31/marketingskills
- ✅ NVIDIA/skills

The remaining 11 were not found in the tier-3 aggregators but are still candidates for manual addition.

## Batch 2 Backlog Repositories

Below is the complete list of 14 repositories from batch_2_backlog. Each needs to be verified by a human reviewer.

### Instructions for Reviewers

For each repository:

1. **Check if it exists**: Visit the GitHub URL and verify the repository is accessible
2. **Verify SKILL.md files**: Look for SKILL.md files in the repository
3. **Check license**: Determine the repository's license and per-skill licenses (if they vary)
4. **Assess quality**: Is this a legitimate skill repository or a low-quality aggregator copy?
5. **Determine patterns**: Identify the glob patterns for locating SKILL.md files
6. **Add to sources.json**: If approved, follow the S1-2 process to register the source
7. **Mark as verified**: Set `verified: true` only after human review

### Repository Checklist

- [ ] **langchain-ai/langchain-skills**
  - URL: https://github.com/langchain-ai/langchain-skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **flutter/skills**
  - URL: https://github.com/flutter/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [x] **NVIDIA/skills**
  - URL: https://github.com/NVIDIA/skills
  - Found in aggregators: Yes (VoltAgent, TravisVN)
  - Notes: _Found by discovery tool_

- [ ] **Shopify/shopify-ai-toolkit**
  - URL: https://github.com/Shopify/shopify-ai-toolkit
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [x] **cloudflare/security-audit-skill**
  - URL: https://github.com/cloudflare/security-audit-skill
  - Found in aggregators: Yes (VoltAgent)
  - Notes: _Found by discovery tool_

- [ ] **google-labs-code/stitch-skills**
  - URL: https://github.com/google-labs-code/stitch-skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **callstackincubator/agent-skills**
  - URL: https://github.com/callstackincubator/agent-skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **better-auth/skills**
  - URL: https://github.com/better-auth/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **clerk/skills**
  - URL: https://github.com/clerk/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **firecrawl/skills**
  - URL: https://github.com/firecrawl/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **tavily-ai/skills**
  - URL: https://github.com/tavily-ai/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [x] **coreyhaines31/marketingskills**
  - URL: https://github.com/coreyhaines31/marketingskills
  - Found in aggregators: Yes (VoltAgent)
  - Notes: _Found by discovery tool_

- [ ] **emilkowalski/skills**
  - URL: https://github.com/emilkowalski/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

- [ ] **prisma/skills**
  - URL: https://github.com/prisma/skills
  - Found in aggregators: No
  - Notes: _To be filled by reviewer_

## Next Steps

1. A maintainer should review each unchecked repository
2. For approved repositories, use `atlas sources import` (when S1-2 is implemented) or manually add to `index/sources.json`
3. Set `verified: true` only after human verification
4. Document any repositories that should be excluded and why

## Related

- Task: S1-9 (Discover awesome)
- Seed batch file: `docs/research/2026-09-24/seed-batch-1.json`
- Discovery output: `build/candidates.jsonl` (246 candidates total)
- Next task: S1-2 (Register sources)
