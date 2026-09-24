# Agent Skills: spec and cross-vendor adoption (verified 2026-09-24)

**Primary sources:** agentskills/agentskills @`69ef37e` (2026-08-09, confirmed as `main` via ls-remote on 2026-09-24); source code of vercel-labs/skills @`7407f38`, cli/cli @`b6770c8`, and openai/codex @`29f056c`; vendor docs extracted 2026-09-24. Claims marked **UNVERIFIED** come only from secondary sources.

## 1. SKILL.md format (current spec)

Source: https://agentskills.io/specification (`docs/specification.mdx`)

| Field | Req. | Constraint |
|---|---|---|
| `name` | yes | 1–64 chars; lowercase `a-z`, `0-9`, `-`; no leading, trailing or `--` hyphens; **must equal parent dir name** |
| `description` | yes | 1–1024 chars, non-empty; should say what the skill does *and* when to use it |
| `license` | no | Free text: a license name or a bundled file reference (the spec's own example is `Proprietary. LICENSE.txt has complete terms`). Not SPDX-enforced |
| `compatibility` | no | 1–500 chars; environment needs (product, packages, network) |
| `metadata` | no | map of string → string, for client-defined keys ("reasonably unique" names) |
| `allowed-tools` | no | space-separated string of pre-approved tools; **Experimental** |

- ASCII regex: `^[a-z0-9]+(-[a-z0-9]+)*$` (https://opencode.ai/docs/skills/). The spec text says "unicode lowercase alphanumeric". skills-ref applies NFKC and `str.isalnum()`, so `café` passes. I tested this locally. The Cloudflare RFC and OpenCode restrict names to ASCII. This is an **unresolved divergence**.
- **Body:** free-form; the spec recommends <5000 tokens and <500 lines. File references are relative and one level deep.
- **Directory:** only `SKILL.md` is required. `scripts/`, `references/` and `assets/` are recommendations, and other files are explicitly allowed (commit `675602e`, 2026-03-20).
- **Progressive disclosure:** (1) name and description, about 50–100 tokens per skill, loaded at startup; (2) the full body on activation; (3) resources on demand (https://agentskills.io/client-implementation/adding-skills-support).
- **Unknown top-level keys:** the spec is silent, and implementations disagree. skills-ref rejects them. claude.ai uploads, the Skills API and `package_skill.py` fail with a hard error (https://code.claude.com/docs/en/skills). The client guide recommends lenient loading, and OpenCode ignores them. Agent Plugins requires clients to skip non-conforming skills (https://agent-plugins.org/specification §7.1).
- **Vendor extension keys** that appear in the wild:
  - Claude Code: about 14 keys, including `when_to_use`, `disable-model-invocation`, `user-invocable`, `model`, `effort`, `context: fork`, `hooks`, `paths`.
  - Cursor: `paths`, `disable-model-invocation`, `icon`, `color` (https://cursor.com/docs/skills).
  - Codex: `metadata.short-description`, plus a sidecar file `agents/openai.yaml` that holds interface and icon data and tool `dependencies` (codex-rs/skills/src/interface.rs).

## 2. Reference validator: skills-ref

Source: https://github.com/agentskills/agentskills/tree/main/skills-ref

- Python package, Apache-2.0, v0.1.0, author Keith Lazuka (Anthropic). Its README says it is "intended for demonstration purposes only… not meant to be used in production", and the project is not accepting code contributions (CONTRIBUTING.md).
- To install: `cd skills-ref && uv sync && source .venv/bin/activate`, or `pip install -e .`.
- CLI commands: `skills-ref validate DIR`, `skills-ref read-properties DIR` (prints JSON), `skills-ref to-prompt DIR…` (prints an `<available_skills>` XML block).
- Python API: `validate`, `read_properties`, `to_prompt`.
- **What it actually checks** (verified by running it):
  - strictyaml parsing (all values come back as strings) and the allowed-key set. A top-level `version:` or `disable-model-invocation:` fails.
  - `name` rules, the directory match, and length limits on `description` and `compatibility`. It accepts a lowercase `skill.md`.
  - It does **not** check `license`, `allowed-tools`, directory contents or body length. The Tavily digest claimed it checks subdirectories; that is wrong.
- **Stricter options:** agent-ecosystem/skill-validator (links, token counts; https://github.com/agent-ecosystem/skill-validator) and `gh skill publish --dry-run`.

## 3. Governance and changes during 2026

- The repo's first commit was 2025-12-16. The spec was published on 2025-12-18 (commit `f990ba1`). Code is Apache-2.0 and docs are CC-BY-4.0.
- The README says only: "originally developed by Anthropic, released as an open standard". CONTRIBUTING says "Logo requests are reviewed by the Anthropic team" and "We don't maintain a directory of community skills." No foundation is named.
- **Agent Skills is not an AAIF project.** https://aaif.io/projects, fetched 2026-09-24, lists MCP, goose, AGENTS.md, agentgateway, A2A and Agent Router. Claims that AAIF "stewards" Agent Skills (e.g., agentman.ai, and Tavily's synthesized answer) are **contradicted**.
- **2026 changes were clarifications only.** No new fields were added and no version field was introduced:
  - March 2026 (`08d1d68`, `99b8edf`, `675602e`, `6f92fcd`): wording, examples, and optional dirs declared non-exhaustive.
  - `6868401`, 2026-05-16: digits added to the name character range.
  - `3f3bbec`, 2026-08-03: `metadata` is string→string.
  - The client-implementation guide was added 2026-03-05 (#200).
  - Tavily's claim that "2026 added license/compatibility/metadata/allowed-tools" is **false**. All six fields were already in the Dec-2025 spec.
- **Open proposals, none adopted:** `skills.json` manifest (#210), `owner/repo@skill:version` cross-refs (#257), SemVer (#415), `.well-known` discovery (#255), `dependencies` (#485), model targeting (#495), XDG paths (#513) (https://github.com/agentskills/agentskills/issues, /discussions).
- **Adjacent standards:**
  - **Agent Plugins 1.0**, 2026-08-06, https://agent-plugins.org: independently governed and "not an AAIF project" (https://aaif.io/blog/from-skills-and-tools-to-portable-agent-plugins). Its TSC is Amazon, Cursor, Microsoft, OpenAI and Vercel, with Google joining (https://developers.googleblog.com/agent-plugins-package-your-skills-tools-and-more).
  - The MCP **Skills Over MCP WG**, which exposes skills as `skill://` resources (https://modelcontextprotocol.io/community/working-groups/skills-over-mcp).

## 4. Version: there is no standard field

The spec has no `version` field, and skills-ref rejects a top-level one. The spec's only example is `metadata.version: "1.0"`, a string. In practice, versions show up in these forms:

- **Git provenance.** `gh skill install` writes `metadata.github-repo`, `github-ref`, `github-tree-sha`, `github-path` and `github-pinned` into the installed SKILL.md. It supports `@TAG`/`@SHA` and `--pin` (https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills; cli/cli `internal/skills/frontmatter`).
- **Content hashes.** Vercel's project `skills-lock.json` stores `computedHash` (SHA-256 over sorted relpath+bytes). Its global `~/.agents/.skill-lock.json` stores the GitHub tree SHA (`skillFolderHash`), `ref` and `skillPath`. gh CLI writes the *same* lock v3 format for interop.
- **Well-known digest:** `sha256:<hex>` of the artifact bytes. RFC v0.2.0 *removed* its `version` field.
- **Package level:**
  - Claude Code `plugin.json`/marketplace `version` pins updates, and `source` accepts `ref` plus a 40-char `sha` (https://code.claude.com/docs/en/plugin-marketplaces).
  - Agent Plugins `plugin.json` `version`: SemVer is RECOMMENDED, but clients MUST NOT reject non-SemVer values.
- **Claude API:** Anthropic skills use date versions (`20251013`) or `latest`. Custom skills use `skver_…` IDs or `latest` (https://docs.claude.com/en/api/skills-guide).

## 5. Discovery and registry mechanisms

- **Spec:** it does not say where skills live. The client guide recommends scanning `.<client>/skills` and `.agents/skills` at both project and user level, with project overriding user.
- **`/.well-known/agent-skills/index.json`** (Cloudflare RFC v0.2.0, **Draft**; published 2026-01-17, updated 2026-03-12; Apache-2.0; https://github.com/cloudflare/agent-skills-discovery-rfc):
  - The index has `$schema: https://schemas.agentskills.io/discovery/0.2.0/schema.json` and `skills[]`. Each entry has `name`, `type` (`skill-md` or `archive`: `.tar.gz`/`.zip` with `SKILL.md` at root), `description`, `url` and `digest`. The legacy v0.1 path is `/.well-known/skills/`, with `files[]`.
  - Live indexes: developers.cloudflare.com (14 archives) and agentskills.io itself (1 skill). The agentskills.io skill is generated by Mintlify and served as lowercase `skill.md` with frontmatter `name: Agent`. That capitalized name **violates the spec's own naming rule**. Its digest matches, which I verified.
  - Consumed by `npx skills`, which tries `agent-skills` first and then the legacy `skills` path (`src/providers/wellknown.ts`).
- **Claude Code `.claude-plugin/marketplace.json`:** `name`, `owner`, `plugins[]`. Each entry has a `source` (relative path, `github{repo,ref,sha}`, `url`, `git-subdir`, `npm`, `archive{url,sha256}` or `command`), plus `version`, `license` (SPDX), `keywords`, `tags`, `category` and `skills[]`. anthropics/skills ships five plugins from one repo.
- **Cursor:** installs skills from a repo only through plugins (`.cursor-plugin/marketplace.json`) or a team marketplace.
- **Agent Plugins:** `plugin.json` has a closed schema (`$schema` and `name` required; `version`, `license`, `keywords` and others optional). Skills live only at `skills/<name>/SKILL.md`. Registries are explicitly out of scope.
- **`npx skills`** (vercel-labs/skills v1.7.0, MIT; launched 2026-01-20 per https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem):
  - Sources: any git host, local paths, direct SKILL.md or archive URLs, and well-known endpoints.
  - It scans `skills/` (including `.curated`, `.experimental`, `.system`) plus about 60 agent directories, up to depth 3, and reads skills declared in `.claude-plugin` manifests.
  - It has 79 `--agent` IDs. Install telemetry feeds skills.sh.
- **`gh skill`** (public preview, gh ≥2.90.0): `search`, `preview`, `install`, `update` and `publish`, with 48 agent hosts in its registry.

## 6. Product adoption table

| Product | Since | Project paths | User paths | Install / distribution |
|---|---|---|---|---|
| Claude Code / claude.ai / API | 2025-10-16 (https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | `.claude/skills` (+ nested, `--add-dir`); `<plugin>/skills` | `~/.claude/skills`; enterprise managed dir | `/plugin marketplace add` + `/plugin install`; claude.ai upload; Skills API. Docs do not mention `.agents/skills` |
| OpenAI Codex | Dec 2025, experimental with `--enable skills` (https://simonwillison.net/2025/Dec/12/openai-skills) | `.codex/skills`; `.agents/skills` from cwd up to the project root | `~/.agents/skills`; `$CODEX_HOME/skills` (deprecated); `.system`; admin config dir | plugins; `agents/openai.yaml` sidecar (codex `host_roots.rs`) |
| ChatGPT | Dec 2025, as `/home/oai/skills` (same source); Skills GA for Business, Enterprise, Healthcare and Edu | n/a | workspace | Upload a skill folder, or create one with the built-in skill-creator. Enterprise has skills on by default from 2026-07-23 (https://help.openai.com/en/articles/20001066-skills-in-chatgpt) |
| GitHub Copilot (cloud agent, CLI, code review, app, JetBrains) | 2025-12-18 (https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills) | `.github/skills`, `.claude/skills`, `.agents/skills` | `~/.copilot/skills`, `~/.agents/skills` | `gh skill` |
| VS Code | Insiders Dec 2025; stable in 1.108 (2026-01-08) | as Copilot | as Copilot, plus `~/.claude/skills` | Agent Plugins, `/skills` |
| Cursor | 2.4, Jan 2026 (https://cursor.com/changelog/2-4) | `.agents/skills`, `.cursor/skills` (nested; also `.claude`, `.codex`) | `~/.agents/skills`, `~/.cursor/skills` (+`~/.claude`, `~/.codex`) | plugins/marketplace; Cloud sync syncs only `~/.cursor/skills` |
| Gemini CLI | v0.23.0 preview 2026-01-07; on by default from v0.26.0 (2026-01-27) (https://geminicli.com/docs/changelogs) | `.gemini/skills` or `.agents/skills` (the alias wins) | `~/.gemini/skills` or `~/.agents/skills` | `gemini skills install <git\|path> [--path] [--scope]`; extensions. Replaced by Antigravity CLI for unpaid users on 2026-06-18 |
| OpenCode | **UNVERIFIED** date | `.opencode/skills`, `.claude/skills`, `.agents/skills` (walks up to the git root) | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | Recognizes only the name, description, license, compatibility and metadata fields; ignores the rest |
| Goose, Windsurf, Kiro, Amp, Junie, Roo | **UNVERIFIED** | `.<agent>/skills` (Amp uses `.agents/skills`) | mostly `~/.<agent>/skills` | Paths per the vercel-labs/skills README table |

- The agentskills.io showcase lists **46 clients** (`docs/snippets/clients.jsx`), each with a public, working implementation. `.agents/skills` is the de facto shared path; Claude Code is the notable holdout.

## 7. Other facts that affect an index

- **Conformance in the wild** (arXiv 2607.00911): `name` matches the dir in 97.65% of curated-marketplace skills vs 91.23% of personal ones; optional fields appear in only 3–16%.
- **Names are not globally unique.** Clients resolve collisions by scope precedence; plugins namespace them (`plugin:skill`).
- **Installed copies are mutated** (gh injects `metadata.github-*`), so their hashes won't match upstream.
- **Licenses are per skill, not per repo.** anthropics/skills mixes Apache-2.0 skills with `license: Proprietary. LICENSE.txt has complete terms` (docx, pdf, pptx, xlsx).
- **Trust:** GitHub says "Skills are not verified by GitHub and may contain prompt injections…". Gemini CLI and the client guide gate project-level skills behind a trust check.

## 8. Implications for Skill Atlas

1. **Identity.** Make the primary key the location, `{host}/{owner}/{repo}/{path-to-skill-dir}`. Keep `name` as a non-unique attribute. Add `name_raw`, `name_matches_dir` and `namespace` (plugin or category).
2. **Replace the required semver `version`** with `source_ref`, `source_commit` (40-char SHA), `tree_sha`, `skill_md_sha256` (raw bytes; the same as the well-known `digest`), `folder_sha256` (Vercel algorithm, for dedup), an optional unvalidated `declared_version` (from `metadata.version`), and `package_version` (from plugin.json or the marketplace). Compute hashes for **both layers**, not only curated.
3. **Frontmatter capture:** `frontmatter_raw`, the six spec fields (typed), `extensions{}` for non-spec keys, `dialects[]` (inferred: `claude-code`, `cursor`, `codex-openai-yaml`), and `conformance: {strict, lenient}` with errors. Never drop source-layer entries on a strict failure.
4. **License:** record `license_declared` (raw), `license_spdx` (resolved), `license_evidence` (`frontmatter`, `bundled-file` or `repo-LICENSE`) and `license_file`. Decide curated eligibility **per skill**, not per repo.
5. **Distribution metadata:** `packaging[]` (`bare`, `claude-plugin`, `cursor-plugin`, `agent-plugin`, `well-known`), `plugin{name, marketplace, manifest_path}`, and generated `install{npx, gh, claude_plugin, well_known_url}` commands.
6. **Crawler patterns (sources layer):** `skills/**/SKILL.md` (depth ≤3, including dot-subdirs); every `.<agent>/skills` directory in Vercel's list; `.claude-plugin/`/`.cursor-plugin/marketplace.json` and Agent Plugins `plugin.json`; per-domain `/.well-known/agent-skills/index.json`, falling back to `/.well-known/skills/`. Accept lowercase `skill.md`, and repair colon-broken YAML the way Codex does.
7. **Dedup:** before hashing, strip provenance keys (`metadata.github-*`, `local-path`, `mintlify-proj`). Ignore `.skill-lock.json` and `skills-lock.json` trees and treat them as installed copies, not upstream sources.
8. **Publish Atlas in the ecosystem's formats.** Emit the curated layer as a v0.2.0 `/.well-known/agent-skills/index.json` (GitHub Pages), a `.claude-plugin/marketplace.json` and an Agent Plugins `plugin.json`. Then `npx skills add`, `gh skill install` and `/plugin install` can consume Atlas directly, and the router becomes installable.
9. **Compatibility field.** Store the raw `compatibility` string and `targets[]` (inferred). Mark `portable: false` when the skill has extension keys or would fail upload to claude.ai or the Skills API.
10. **Freshness:** track `first_seen`, `last_seen`, `upstream_status`, and `spec_commit_checked`. The spec has no version number to pin to.
