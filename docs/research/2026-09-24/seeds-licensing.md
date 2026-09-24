# Seed batch 1 + licensing policy (as of 2026-09-24)

**How this was checked.** Calls to `api.github.com/repos/*` returned `403` (not enabled for this session), so:
- **Skill counts and licenses:** blobless shallow `git clone` of each default-branch HEAD; `git ls-tree` for counts; LICENSE/NOTICE/SKILL.md checked out and classified myself.
- **GitHub's license detection:** shields.io license badge, cross-check only.
- **Stars (estimated, third-party):** exact = LinklyAI snapshot (https://github.com/LinklyAI/best-skills/blob/main/data/2026-09-24/rankings/top-repos.csv); **≈** = rounded shields.io value.
- **last_commit:** HEAD committer date, in place of `pushed_at`.

Raw per-repo analysis was produced in a scratch environment and is not committed; `seed-batch-1.json` in this folder is the machine-readable form of the table below.

**Legend.** Verified: `n`, last_commit, licenses (read from files). `n` = SKILL.md files (unique names after the slash), all counted from the git tree; allow/cond/deny/unk = unique skills per class under the §2 algorithm. URLs are `https://github.com/<repo>`.

## 1. Seed batch 1

| # | id | repo | owner_type | repo license (SPDX) | per-skill varies | skill_pattern | n | last_commit | stars | curated_eligible |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | anthropic-skills | anthropics/skills | vendor | **none at root** (GitHub: not specified) | **y**: per-skill LICENSE.txt, 14 Apache-2.0, 4 proprietary (docx/pdf/pptx/xlsx), 2 none (doc-coauthoring, template) | `skills/*/SKILL.md` | 20 | 2026-09-10 | 177,828 | **partial** 14 yes / 4 no / 2 hold |
| 2 | anthropic-claude-plugins-official | anthropics/claude-plugins-official | vendor | Apache-2.0 | **y**: 18 plugin-level LICENSEs; `plugins/claude-security` proprietary | `{plugins,external_plugins}/*/skills/*/SKILL.md` | 31/27 | 2026-09-23 | 36,663 | **partial** 26 yes, 1 no |
| 3 | anthropic-knowledge-work-plugins | anthropics/knowledge-work-plugins | vendor | Apache-2.0 | y: 17 plugin LICENSEs (13 Apache, 4 MIT) | `**/skills/*/SKILL.md` | 252/232 | 2026-09-23 | ≈26k | **yes** (attribution per plugin) |
| 4 | openai-skills | openai/skills (**deprecated**) | vendor | **none at root** | **y**: 31 Apache-2.0, 5 MIT (Notion Labs, Vercel), 8 Figma Developer Terms | `skills/.{curated,system}/*/SKILL.md` | 44/43 | 2026-06-23 | 27,591 | **partial** 35 yes as frozen snapshot, 8 no |
| 5 | openai-plugins | openai/plugins | vendor (bundles 3rd-party) | **none** | **y**: 118 allow, 13 deny, 387 unk | `plugins/*/skills/*/SKILL.md` | 536/518 | 2026-09-11 | 7,137 | **partial** ≈118 yes; rest pointer-only |
| 6 | google-skills | google/skills | vendor | Apache-2.0 | n | `skills/**/SKILL.md` (skip `plugins/**` copies) | 152/147 | 2026-09-23 | 20,324 | yes |
| 7 | google-gemini-skills | google-gemini/gemini-skills | vendor | Apache-2.0 | n | `skills/*/SKILL.md` | 3 | 2026-09-23 | ≈4.2k | yes |
| 8 | firebase-agent-skills | firebase/agent-skills | vendor | Apache-2.0 | n | `skills/*/SKILL.md` | 13 | 2026-09-22 | ≈453 | yes |
| 9 | microsoft-skills | microsoft/skills | vendor | MIT | n (181 frontmatter MIT) | `.github/plugins/*/skills/*/SKILL.md`, `.github/skills/*/SKILL.md`, **60 symlinks: do not follow** | 204/202 | 2026-09-23 | ≈3.1k | yes |
| 10 | microsoft-azure-skills | microsoft/azure-skills | vendor | MIT | n | `skills/*/SKILL.md` (copy in `.github/plugins`) | 84/47 | 2026-09-23 | ≈1.5k | yes |
| 11 | dotnet-skills | dotnet/skills | vendor | MIT | n | `plugins/*/skills/*/SKILL.md` | 108 | 2026-09-23 | ≈5.5k | yes |
| 12 | github-awesome-copilot | github/awesome-copilot | vendor host, community-contributed | MIT | y: 8 skill-level LICENSEs, 1 NOTICE, 7 frontmatter/file conflicts | `skills/**/SKILL.md` | 441 | 2026-09-24 | 39,323 | yes (review the 7 conflicts) |
| 13 | vercel-agent-skills | vercel-labs/agent-skills | vendor | **no LICENSE file**; README says "MIT" | y: 4 frontmatter MIT, 5 none | `skills/*/SKILL.md` | 9 | 2026-08-28 | 31,491 | **partial** 4 yes, 5 hold |
| 14 | huggingface-skills | huggingface/skills | vendor | Apache-2.0 | n | `skills/*/SKILL.md`, `hf-mcp/skills/*/SKILL.md` | 26 | 2026-09-23 | 11,092 | yes |
| 15 | cloudflare-skills | cloudflare/skills | vendor | Apache-2.0 | n | `skills/*/SKILL.md` | 14 | 2026-09-22 | ≈2.9k | yes |
| 16 | supabase-agent-skills | supabase/agent-skills | vendor | MIT | n | `skills/*/SKILL.md` | 2 | 2026-08-12 | ≈2.6k | yes |
| 17 | stripe-ai | stripe/ai | vendor | MIT | n | `skills/*/SKILL.md` (ignore 5 `providers/*` copies) | 60/10 | 2026-09-24 | ≈1.8k | yes |
| 18 | sentry-for-ai | getsentry/sentry-for-ai | vendor | MIT | **y: all 34 frontmatter say Apache-2.0** | `src/skills/*/SKILL.md` (+ frozen `skills-legacy/*`) | 34 | 2026-09-21 | ≈266 | yes, shipping both license texts |
| 19 | sentry-skills | getsentry/skills | vendor | Apache-2.0 | y: `security-review` CC-BY-SA-4.0 (OWASP-derived) | `skills/*/SKILL.md` | 27 | 2026-08-25 | ≈1k | **partial** 26 yes, 1 conditional |
| 20 | neon-agent-skills | neondatabase/agent-skills | vendor | Apache-2.0 | n | `skills/*/SKILL.md` (copy in `plugins/`) | 17/9 | 2026-09-23 | ≈90 | yes |
| 21 | expo-skills | expo/skills | vendor | MIT | n | `plugins/*/skills/*/SKILL.md` | 26 | 2026-09-22 | ≈2.6k | yes |
| 22 | notion-skills | makenotion/skills | vendor | MIT (LICENSE.md) | n | `skills/*/SKILL.md` | 2 | 2026-09-22 | ≈168 | yes |
| 23 | hashicorp-agent-skills | hashicorp/agent-skills | vendor | MPL-2.0 | n | `plugins/*/skills/*/SKILL.md` | 20 | 2026-09-03 | ≈873 | **conditional** (MPL-2.0) |
| 24 | remotion-skills | remotion-dev/skills | vendor | **none** (no LICENSE, frontmatter or package.json license) | n | `skills/*/SKILL.md` | 12 | 2026-09-22 | ≈4.7k | **no**: Unknown, pointer-only |
| 25 | figma-mcp-server-guide | figma/mcp-server-guide | vendor | **none**; README points to Figma Developer Terms | n | `{skills,skills-figquery,workflow-skills}/*/SKILL.md` | 30/16 | 2026-09-22 | ≈2k | **no**: terms grant use only |
| 26 | obra-superpowers | obra/superpowers | community | MIT | n | `skills/*/SKILL.md` | 15 | 2026-09-18 | 290,678 | yes |
| 27 | mattpocock-skills | mattpocock/skills | community | MIT | n | `skills/*/*/SKILL.md` (exclude `in-progress/`) | 38 (9 in-progress) | 2026-09-18 | 268,489 | yes |
| 28 | addyosmani-agent-skills | addyosmani/agent-skills | community | MIT | n | `skills/*/SKILL.md` | 25 | 2026-09-22 | 98,713 | yes |
| 29 | kepano-obsidian-skills | kepano/obsidian-skills | community | MIT | n | `skills/*/SKILL.md` | 6 | 2026-09-15 | 48,813 | yes |
| 30 | kdense-scientific-agent-skills | K-Dense-AI/scientific-agent-skills (renamed from claude-scientific-skills; same HEAD `49c6e97`) | community (company) | MIT (LICENSE.md) | **y**: frontmatter includes BSD/Apache/GPL/PolyForm-NC/URLs/"Unknown", plus 4 copies of Anthropic proprietary skills | `skills/*/SKILL.md` | 166 | 2026-09-21 | 46,340 | **partial** ≈144 yes / 6 no / 16 review |
| 31 | wshobson-agents | wshobson/agents | community | MIT | n | `plugins/*/skills/*/SKILL.md` | 183 | 2026-09-13 | 39,911 | yes |
| 32 | trailofbits-skills | trailofbits/skills | community (security firm) | CC-BY-SA-4.0 | n | `plugins/*/skills/*/SKILL.md` | 85 | 2026-09-21 | ≈7.2k | **conditional** (ShareAlike) |
| 33 | composio-awesome-claude-skills | ComposioHQ/awesome-claude-skills | aggregator | **no LICENSE file**; README says Apache-2.0 | **y**: includes copies of Anthropic proprietary `document-skills/*` | `*/SKILL.md`, `composio-skills/*/SKILL.md` | 864 | 2026-07-24 | 75,557 | **no**: discovery only |
| 34 | sickn33-agentic-awesome-skills | sickn33/agentic-awesome-skills (renamed from antigravity-awesome-skills) | aggregator/mirror | MIT (code) + `LICENSE-CONTENT` CC-BY-4.0 | **y**: `*-official` copies of Anthropic proprietary skills; AGPL; FSL-1.1-ALv2 | `skills/*/SKILL.md` (3 copies) | 7,653/2,451 | 2026-09-24 | 46,836 | **no**: discovery only |
| 35 | voltagent-awesome-agent-skills | VoltAgent/awesome-agent-skills | aggregator (link list) | MIT | n/a | none | 0 | 2026-09-23 | ≈35k | n/a |
| 36 | travisvn-awesome-claude-skills | travisvn/awesome-claude-skills | aggregator (link list) | **none** | n/a | none | 0 | 2026-04-28 | ≈15k | n/a |

**Dropped or merged** (evidence: `git ls-remote`, clones):
- `getsentry/sentry-agent-skills`: 15 skills, no LICENSE file, last commit 2026-02-28. Superseded by #18.
- `makenotion/claude-code-notion-plugin`: 4 skills, no license, last commit 2026-01-22. The same four Notion skills appear as MIT, "Copyright 2025 Notion Labs", in `openai/skills/skills/.curated/notion-*/LICENSE.txt`.
- `trailofbits/skills-curated`: a vetted third-party mirror, moved to tier 3.
- Not found (`git ls-remote` failed; absent or private): `figma/skills`, `neondatabase/skills`, `aws/agent-skills`, `awslabs/agent-skills`.

openai/skills deprecation: "This repository is deprecated… use the OpenAI Plugins repository" (https://github.com/openai/skills/blob/main/README.md).

## 2. Licensing edge cases and policy

### Edge cases found in batch 1

1. **No root LICENSE, per-skill terms only** (anthropics/skills, openai/skills). GitHub detects no license, so a GitHub-API-only resolver marks a 178k-star repo Unknown. openai/skills README: "The license of an individual skill can be found… in the `LICENSE.txt` file" (https://github.com/openai/skills/blob/main/README.md). Licensee only "compares the repository's LICENSE file" (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).
2. **Proprietary skills inside open repos.** `anthropics/skills/skills/{docx,pdf,pptx,xlsx}/LICENSE.txt`: "All rights reserved… may not… Distribute, sublicense, or transfer" (https://github.com/anthropics/skills/blob/main/skills/docx/LICENSE.txt). Also `claude-plugins-official/plugins/claude-security/LICENSE` (proprietary, in an Apache-2.0 repo) and `openai/plugins/.../earnings-preview/LICENSE.txt` ("Proprietary - Internal Use Only").
3. **Aggregators re-publishing proprietary skills.** ComposioHQ `document-skills/docx`, K-Dense `skills/docx|pdf|pptx|xlsx` and sickn33 `skills/docx-official` carry Anthropic's "All rights reserved" LICENSE.txt inside MIT/Apache-labelled repos. **Never curate from a copy**; resolve to upstream by content hash.
4. **Vendor custom terms.** Figma skills (`openai/skills/.curated/figma*/LICENSE.TXT`, figma/mcp-server-guide README) fall under the Figma Developer Terms, which grant only a "limited license to access and use… only as necessary to develop, test, and support an integration" (https://www.figma.com/legal/developer-terms/). Not redistributable.
5. **Frontmatter and license file disagree.** sentry-for-ai: frontmatter `Apache-2.0`, root MIT (all 34 skills). awesome-copilot `anti-ui-slop`: frontmatter MIT, skill LICENSE Apache-2.0. K-Dense frontmatter often describes the *wrapped library*, not the skill: `matplotlib` links to matplotlib's LICENSE, `bioservices` says "GPLv3 license", `deepspot-m` says `PolyForm-Noncommercial-1.0.0`, while the repo is MIT.
6. **Free-text values.** The spec allows "License name or reference to a bundled license file" and uses "Proprietary. LICENSE.txt has complete terms" as its example (https://agentskills.io/specification). Seen: `Complete terms in LICENSE.txt`, `LICENSE`, `MIT license`, `3-clause BSD license`, `Biopython License Agreement`, `Unknown`, URLs, `AGPL-3.0 (referencing Twitter's algorithm source)`, `CC-BY-4.0 AND Apache-2.0`. Only 11.25% of 1.43M skills declare a license (https://arxiv.org/html/2607.01136v1).
7. **README-only license:** vercel-labs/agent-skills ("MIT"), ComposioHQ ("Apache License 2.0"), Figma terms. GitHub detects nothing.
8. **No license at all:** remotion-dev/skills, travisvn, makenotion plugin. That means no redistribution rights: "No license declared… no rights… beyond what copyright default allows" (https://github.com/anthropics/claude-for-legal/blob/main/legal-builder-hub/skills/skill-installer/SKILL.md).
9. **Copyleft, ShareAlike, non-commercial:** trailofbits/skills (CC-BY-SA-4.0); getsentry `security-review` (CC-BY-SA, OWASP-derived); hashicorp (MPL-2.0); skills-curated `wooyun-legacy` (CC-BY-NC-SA-4.0 inside a CC-BY-SA repo); K-Dense GPL-2.0/GPL-3.0-or-later/PolyForm-NC; sickn33 `FSL-1.1-ALv2` (https://spdx.org/licenses/FSL-1.1-ALv2.html) and `AGPL-3.0-only`. BY-SA 4.0 is only one-way compatible, with GPLv3 (https://creativecommons.org/share-your-work/licensing-considerations/compatible-licenses/).
10. **Separate code/content licenses:** sickn33 `LICENSE` (MIT, code) vs `LICENSE-CONTENT` (CC-BY-4.0, "original non-code repository content"), so SKILL.md prose is CC-BY-4.0.
11. **Plugin-level license files** (nearest-ancestor lookup needed): claude-plugins-official 18, knowledge-work-plugins 17, openai/plugins 8, skills-curated 23.
12. **NOTICE files:** `openai/skills/.curated/playwright*/NOTICE.txt` (derived from microsoft/playwright-cli), `awesome-copilot/skills/anti-ui-slop/NOTICE`, `claude-plugins-official/plugins/claude-security/NOTICE.md`, and `anthropics/skills/THIRD_PARTY_NOTICES.md` (lists BSD-2 and GPL-3.0 components bundled in scripts).
13. **Messy license files:** `LICENSE.TXT`/`.txt`/`.md` variants; pointer-only files such as getsentry `django-perf-review/LICENSE` ("Apache License 2.0… See repository root LICENSE").
14. **Copies and symlinks:** microsoft/skills has 60 symlinks, stripe/ai 6 copies, figma 2, sickn33 3 trees (7,653 files, 2,451 names). Resolve once per canonical path; never follow symlinks.

### License-resolution algorithm (per skill, at a pinned commit SHA)

0. **Canonicalize:** skip symlinks, choose the path by `skill_pattern`, hash SKILL.md and bundled files.
1. **Frontmatter `license`** (top-level key; `metadata.license` is a hint only). Normalize: trim quotes and a trailing "license"; map aliases (`MIT License`→`MIT`, `Apache License, Version 2.0`→`Apache-2.0`, `3-clause BSD`→`BSD-3-Clause`, CC deed URL→`CC-BY-x.0`); parse as an SPDX expression.
   - File reference (`LICENSE`, `…LICENSE.txt has complete terms`): go to step 2 with that file. If missing, it's a dangling reference: **Unknown**.
   - Starts with `Proprietary`: `LicenseRef-Proprietary` (deny).
   - Unparseable, third-party URL or `Unknown`: `LicenseRef-Unrecognized`, **manual review**, no automatic fall-through (the claude-for-legal installer rule).
2. **Skill-folder LICENSE/LICENCE/COPYING** (any case, `.txt/.md/.rst`): ScanCode or Licensee at ≥90% confidence; name-match one-line pointer files; custom text becomes `LicenseRef-<vendor>-terms` (deny).
3. **Nearest ancestor license file** between skill folder and root (plugin level). Nearest wins.
4. **Root LICENSE**, identified by our own scanner; GitHub `/license` is a cross-check only (root files only). With split files (`LICENSE-CONTENT`, `LICENSE-DOCS`), SKILL.md and `references/` take the content license and `scripts/` the code license.
5. **README "License" section:** store as `license_declared_readme`; **not enough for curation** without maintainer sign-off.
6. Otherwise **`Unknown`** (SPDX `NOASSERTION`).

**Conflicts:** store `license_declared` (frontmatter) and `license_concluded` (files) separately. If both are allowlisted, conclude `<a> AND <b>`, ship both texts, open an upstream issue (sentry-for-ai becomes `Apache-2.0 AND MIT`). If either is conditional or denied, take the more restrictive and block automatic curation (K-Dense GPL/PolyForm skills stay out).

**Bundled files:** scan `scripts/`, `references/`, `assets/` too; every mirrored file must resolve to the allowlist (e.g. the GPL-3.0 components in Anthropic's THIRD_PARTY_NOTICES).

**Re-syncs:** store the commit SHA and license-file hash. If a re-sync leaves the allowlist, freeze the last compatible snapshot (`docs/inclusion-criteria.md`, "Upstream License Changes").

### Allowlist for curated redistribution

- **Auto-allow:** MIT, MIT-0, 0BSD, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0, CC-BY-4.0, CC0-1.0, Unlicense, Zlib.
- **Conditional** (maintainer approval, verbatim only, flagged `share_alike`/`weak_copyleft`): MPL-2.0, LGPL-* (already "acceptable" in the inclusion criteria) and **CC-BY-SA-4.0**. The criteria don't cover CC-BY-SA yet; I recommend allowing it verbatim under its own license, never merged into an MIT compilation.
- **Deny** (source layer only): GPL-*, AGPL-*, CC-BY-NC*, CC-BY-ND*, PolyForm-*, FSL-*, BUSL-*, SSPL, `LicenseRef-Proprietary`, vendor terms (Anthropic proprietary, Figma), `NOASSERTION`/Unknown/unrecognized.
- **Allowlist edits:** maintainers only, by PR; never added from a license string read upstream.

### What curated/ has to carry

- **Every curated skill:** `curated/<id>/LICENSE` (upstream text verbatim, never regenerated from an SPDX template) plus `ATTRIBUTION.md` or metadata recording upstream URL, path, commit SHA, copyright holder(s), SPDX expression, and "modifications: UTF-8/LF normalization only".
- **Apache-2.0** (§4, https://www.apache.org/licenses/LICENSE-2.0): (a) include the license; (b) note changes on modified files; (c) keep copyright and attribution notices; (d) if a NOTICE applies (skill, plugin or root level), copy it verbatim to `curated/<id>/NOTICE` **and** into a combined `curated/NOTICE`.
- **MIT/BSD/ISC:** keep the copyright and permission notice.
- **CC-BY-4.0** (§3(a), https://creativecommons.org/licenses/by/4.0/legalcode.en): creator/attribution parties, copyright notice, license notice and link, disclaimer, source link, and any modifications (Title, Author, Source, License). **CC-BY-SA-4.0** adds: adaptations stay BY-SA.
- **MPL-2.0:** keep the license notice and link to the source.
- **Skill Atlas root LICENSE (MIT):** state that MIT covers only Skill Atlas's own code and metadata; `curated/` files keep their upstream licenses. Consider REUSE-style per-file declarations (https://reuse.software/spec/) and publish a takedown contact.

## 3. Priority order

**Tier 1: official vendors** (crawl daily; first curated candidates, in order):
- anthropics/skills (partial), claude-plugins-official, knowledge-work-plugins
- google/skills, gemini-skills, firebase; microsoft/skills, azure-skills, dotnet
- huggingface, cloudflare, stripe, supabase, neon, expo, notion, sentry-for-ai, getsentry/skills
- github/awesome-copilot (official host, community content: per-skill checks)
- openai/skills (frozen snapshot), openai/plugins (partial), vercel-labs (partial), hashicorp (conditional)
- **Source-only:** figma, remotion

**Tier 2: top community** (weekly): obra/superpowers, mattpocock, addyosmani, kepano, wshobson (all MIT); K-Dense (partial, manual review); trailofbits/skills (conditional, CC-BY-SA).

**Tier 3: aggregators, discovery only:** sickn33, ComposioHQ, VoltAgent, travisvn, trailofbits/skills-curated, LinklyAI/best-skills. Harvest upstream links only; never curate their copies; dedupe by content hash and attribute upstream. Upstreams found this way enter tier 1 or 2 after the same checks.

**Batch 2 backlog** (exist per `git ls-remote`, not yet audited): langchain-ai/langchain-skills, flutter/skills, NVIDIA/skills, Shopify/shopify-ai-toolkit, cloudflare/security-audit-skill, google-labs-code/stitch-skills, callstackincubator/agent-skills, better-auth/skills, clerk/skills, firecrawl/skills, tavily-ai/skills, coreyhaines31/marketingskills, emilkowalski/skills; prisma/skills (9 skills, MIT, verified). Source: https://github.com/LinklyAI/best-skills/blob/main/data/2026-09-24/rankings/official-vendors.csv.
