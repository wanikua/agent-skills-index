# Router & Papers: skill retrieval, routing, and the Agent Skills literature (as of 2026-09-24)

**Method.** Leads from the Tavily search digests and the Tavily Research (pro) report on routing were checked against arXiv full texts, tool source code, live API calls and official docs (Tavily: 0 searches, 2 extracts). Unconfirmed claims are marked **UNVERIFIED**.

## 1. Existing skill-search tools

| Tool | Interface | How it ranks | What it returns | Limitations |
|---|---|---|---|---|
| Vercel `npx skills find` + `find-skills` meta-skill | CLI (interactive or `find <q> [--owner]`) | The CLI calls `GET skills.sh/api/search?q=&limit=20`. The server reports `"searchType":"semantic","searchVersion":"algolia"`. **The CLI then re-sorts results by installs**, which discards the relevance order ([find.ts](https://raw.githubusercontent.com/vercel-labs/skills/main/src/find.ts); live call 2026-09-24) | id, name, source, installs. No description, license or trust field | The meta-skill says to prefer ≥1K installs and repos with ≥100 stars ([SKILL.md](https://raw.githubusercontent.com/vercel-labs/skills/main/skills/find-skills/SKILL.md)): popularity, not fit. |
| skills.sh API v1 | HTTP; Vercel OIDC token only; 600 req/min | Single-word queries use fuzzy matching; multi-word queries use semantic search. `limit` 1–200 ([docs](https://skills.sh/docs/api)) | id, slug, name, source, installs, installUrl, url. A separate `/audit/{source}/{skill}` endpoint | Over 600,000 skills ([Vercel changelog](https://vercel.com/changelog/the-skills-sh-api-is-now-available)). Search results carry no description. |
| SkillsMP REST | `GET /api/v1/skills/search`; 50 req/day anonymous, 500/day with a key | Keyword search. `sortBy=stars` (the default) or `recent` ([docs](https://skillsmp.com/docs/api)) | name, author, description, githubUrl, **repo** stars, updatedAt | `/ai-search` returned 404 on 2026-09-24. The third-party [skillsmp-mcp-server](https://raw.githubusercontent.com/anilcancakir/skillsmp-mcp-server/main/README.md) still advertises `skillsmp_ai_search`, so the two have drifted apart. |
| K-Dense `claude-skills-mcp` | MCP: `find_helpful_skills(task_description, top_k=3 [1–20], list_documents)`, `read_skill_document`, `list_skills` | `all-MiniLM-L6-v2` embeddings of descriptions, ranked by cosine similarity ([api.md](https://raw.githubusercontent.com/K-Dense-AI/claude-skills-mcp/main/docs/api.md), [architecture](https://raw.githubusercontent.com/K-Dense-AI/claude-skills-mcp/main/docs/architecture.md)) | Relevance score 0–1 plus the skill's file list | The tool description says "Always call this tool FIRST…". MiniLM is weaker than BM25 on ToolRet (see §2). |
| Anthropic Tool Search Tool (for tools, not skills; a reference design) | API server tool, regex or BM25 variant, over up to 10,000 `defer_loading` tools | Matches name, description and argument names/descriptions. BM25 queries are capped at 500 characters ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)) | Up to 5 `tool_reference` results by default. Custom (e.g. embedding) search is allowed | Anthropic reports MCP-eval accuracy of 49%→74% on Opus 4 and 79.5%→88.1% on Opus 4.5 ([engineering blog](https://www.anthropic.com/engineering/advanced-tool-use)). Tool choice degrades beyond 30–50 tools (docs). |
| SCOUT (PayPal MCP gateway) | MCP `tool_search` + `execute_tool` | BM25 + dense, reciprocal rank fusion (RRF), 2,000+ tools ([2608.23992](https://arxiv.org/abs/2608.23992)) | Top-k tools | Tool tokens 140.2k → 1.3k. |
| Claude Code native | The model reads a listing of skill names and descriptions | The LLM's own judgment | – | The listing budget is **1% of the context window**, and description plus `when_to_use` is truncated at 1,536 characters ([docs](https://code.claude.com/docs/en/skills)). |

Scale check: of about 1.95M skills collected from six marketplaces, 1,046,565 were unique by content (about 46% duplicates) ([PromptArmor](https://www.promptarmor.com/resources/50-percent-of-skills-include-external-packages-and-urls)). A live skills.sh query for "review my pull request for security bugs" returned 7 different skills all named `security-review`.

## 2. Retrieval research: what the numbers say

**Lexical, dense, hybrid and reranking.** The results depend heavily on the benchmark.
- **SkillRet** (6,006-skill pool, 4,392 long, noisy queries; Table 3 of [2605.05726](https://arxiv.org/abs/2605.05726)), Recall@5:

  | Retriever | Recall@5 |
  |---|---|
  | BM25 | 53.0 |
  | bge-small (33M) | 54.7 |
  | Qwen3-Emb-0.6B | 62.6 |
  | harrier-oss-v1-0.6b, best off-the-shelf (NDCG@10 70.3) | 70.6 |
  | SkillRouter-Emb-0.6B | 73.7 |
  | SkillRet-Emb-0.6B, fine-tuned | 82.4 |
  | SkillRet-Emb-8B, fine-tuned | 88.6 |

  BM25 takes 0.73 ms/query on CPU; Qwen3-Emb-0.6B takes 21 ms on a B200 GPU.
- **SkillRouter** (~80K pool, 75 expert-verified queries). Hit@1: BM25 0.314, BGE-large 0.600, text-embedding-3-large 0.620. The best retrieve-and-rerank pipeline reaches 0.740–0.760 ([2603.22455](https://arxiv.org/abs/2603.22455), Tables 3–4).
- **SRA-Bench** (26,262 skills). There is "no universal winner":
  - Dataset by dataset, BM25 beats BGE on LogicBench (R@10 36.1 vs 20.5) and loses on ToolQA (55.1 vs 83.4).
  - A hybrid mostly improves recall rather than top-1.
  - **An LLM reranking BM25's top 50 was the strongest method.** For example, Qwen3-32B raised ToolQA R@1 from 7.0 to 43.7 ([2604.24594](https://arxiv.org/abs/2604.24594), Table 3 and §5.3).
- **ToolRet** (43K tools, average NDCG@10): BM25s 36.5, all-MiniLM-L6-v2 25.5, e5-large 33.7, ColBERT 23.8 ([2503.01763](https://arxiv.org/abs/2503.01763)).
- **StackOne** (270 MCP tools, 2,700 cases): BM25 top-1 is 14% but **top-5 is 87%**. BM25+TF-IDF reaches 21% top-1 and embeddings 38% ([blog](https://www.stackone.com/blog/mcp-tool-search-bm25-tfidf-hybrid)). This contradicts the digest's Reddit claim that BM25 gets "60–80% top-1", which I treat as anecdotal.
- **RAG-MCP**: retrieval tripled tool-selection accuracy, from 13.62% to 43.13% ([2505.03275](https://arxiv.org/abs/2505.03275)).

**What text to index.**
- Hiding the skill body costs 37–44 percentage points of routing accuracy in the 80K pool. The median description is 21 words; the median body is 704 words ([2603.22455](https://arxiv.org/abs/2603.22455)).
- On SkillRet, Qwen3-Emb-8B scores NDCG@10 48.6 on name+description versus 60.0 on the full document (Table 14).
- Scoring each field separately and fusing the scores beats concatenating them, and the gain grows with library size ([2608.02880](https://arxiv.org/abs/2608.02880)).
- Boilerplate shared across skills hurts ranking. Down-weighting generic high-frequency tokens (identified by IDF) raises Recall@10 by up to 20 points ([2607.18785](https://arxiv.org/abs/2607.18785)).
- Generating pseudo-queries per skill offline adds 6.7 points of Recall@1 on average ([2608.16071](https://arxiv.org/abs/2608.16071)).
- Adding a "route elsewhere when…" negative-boundary field to each skill improves task success by 3.6 points ([2608.04482](https://arxiv.org/abs/2608.04482)).

**More skills hurts.**
- Routing accuracy falls logarithmically with library size (R²>0.97 across 15 LLMs and 1,141 skills). Overly general "black-hole skills" capture requests meant for others. Optimizing the library raised routing accuracy from 71.3% to 91.7% ([2605.16508](https://arxiv.org/abs/2605.16508)).
- Pass rate drops by up to 21% going to a 202-skill library, and the cause is wrong skill selection, not the longer context ([2605.24050](https://arxiv.org/abs/2605.24050)).
- Selection accuracy shows a phase transition as the library grows, driven by how easily similar skills are confused ([2601.04748](https://arxiv.org/abs/2601.04748)).
- Relevant ≠ useful. Agents load skills at similar rates whether or not the gold skill was retrieved ([2604.24594](https://arxiv.org/abs/2604.24594)); a post-retrieval load/skip decision cut activations by 68.5% at equal accuracy ([2609.26863](https://arxiv.org/abs/2609.26863)).
- Treating top-k as a set to fill, with redundancy removed and a token budget enforced, beats independent top-k ([2609.05824](https://arxiv.org/abs/2609.05824), [2608.19993](https://arxiv.org/abs/2608.19993)).

**Context budgets.**
- The spec caps `name` at 64 characters and `description` at 1,024. Metadata is about 100 tokens and the body should stay under 5,000 tokens ([spec](https://agentskills.io/specification), local clone at commit 69ef37e).
- Clients should expect 50–100 tokens per skill in the catalog ([client guide](https://agentskills.io/client-implementation/adding-skills-support)).
- At 1% of a 200K window, Claude Code's listing holds ~2K tokens, roughly 20–40 descriptions (my arithmetic). Large catalogs must be searched, not listed.

**Labels are one-to-many.** 67.9% of tool sub-queries have functionally equivalent answers. Between 30% and 47% of reported fine-tuning gains turned out to be evaluation artifacts ([2609.08327](https://arxiv.org/abs/2609.08327)). Remapping functional equivalents in SkillRet raised NDCG@10 by 3.3 points (Appendix D).

**Fine-tuning risk.** Fine-tuning on synthetic queries alone causes catastrophic forgetting on real queries in a production router with 34,396 skills ([2609.10750](https://arxiv.org/abs/2609.10750)).

## 3. Literature table (arXiv, v1 dates)

| arXiv | Title (short) | v1 | Key finding for us |
|---|---|---|---|
| **Ecosystem measurement** | | | |
| [2602.08004](https://arxiv.org/abs/2602.08004) | Data-Driven Analysis of Claude Skills | 2026-02-08 | 40,285 skills; mostly software engineering; heavy intent-level redundancy |
| [2607.00911](https://arxiv.org/abs/2607.00911) | From Registry to Repository | 2026-07-01 | 41.6K skills; reuse is a one-time copy; 53% never modified |
| [2607.01456](https://arxiv.org/abs/2607.01456) | From Anatomy to Smells | 2026-07-01 | >99% of SKILL.md files have at least one smell, and smells persist |
| [2607.01136](https://arxiv.org/abs/2607.01136) | Skills Are Not Islands | 2026-07-01 | Dependency graphs for 1.43M skills; metadata is "activation-ready but governance-poor" |
| [2609.17274](https://arxiv.org/abs/2609.17274) | After the Party (ClawHub) | 2026-09-15 | Top 10% of skills get 46.9% of downloads; three scanners disagree on 23,702 of 61,990 skills |
| **Security** | | | |
| [2510.26328](https://arxiv.org/abs/2510.26328) | Skills enable trivially simple prompt injections | 2025-10-30 | Instruction-detection defenses do not work, because skills are entirely instructions |
| [2601.10338](https://arxiv.org/abs/2601.10338) | Agent Skills in the Wild | 2026-01-15 | 26.1% of 31,132 skills are vulnerable; skills with scripts are 2.12× more likely to be |
| [2607.12340](https://arxiv.org/abs/2607.12340) | Skills That Don't Exist | 2026-07-14 | Agents invent skill names 36–43% of the time; retrieval grounding cuts this from 40.8% to 3.2% |
| [2609.13353](https://arxiv.org/abs/2609.13353) | **SkillAtlas**: attack-trace library | 2026-09-11 | **Name collision with "Skill Atlas"** |
| **Effectiveness** | | | |
| [2602.12670](https://arxiv.org/abs/2602.12670) | SkillsBench | 2026-02-13 | Curated skills raise pass rate +16.6pp; focused skills (≤3 modules) do best |
| [2603.15401](https://arxiv.org/abs/2603.15401) | SWE-Skills-Bench | 2026-03-16 | 39 of 49 skills give zero gain; average +1.2%; 3 skills hurt |
| [2608.11888](https://arxiv.org/abs/2608.11888) | Skills Can Be Harmful | 2026-08-12 | 307 failures caused by seemingly *relevant* skills |
| [2605.24050](https://arxiv.org/abs/2605.24050) | More Skills, Worse Agents? | 2026-05-21 | "Skill shadowing" (picking the wrong skill) drives the drop in larger libraries |
| [2605.16508](https://arxiv.org/abs/2605.16508) | Scaling Laws of Skills | 2026-05-15 | Log-decay routing law; black-hole skills |
| **Retrieval / routing** | | | |
| [2503.01763](https://arxiv.org/abs/2503.01763) | ToolRet | 2025-03-03 | BM25 competitive with dense retrievers on 43K tools |
| [2603.22455](https://arxiv.org/abs/2603.22455) | SkillRouter | 2026-03-23 | The body is the decisive signal; open 0.6B retriever and reranker (74% Hit@1) |
| [2604.24594](https://arxiv.org/abs/2604.24594) | Skill Retrieval Augmentation (SRA) | 2026-04-27 | 26K-skill benchmark; LLM reranking works best; agents load skills without discrimination |
| [2605.05726](https://arxiv.org/abs/2605.05726) | SkillRet | 2026-05-07 | 63K training samples; fine-tuned models reach NDCG@10 86 |
| [2606.03565](https://arxiv.org/abs/2606.03565) | R3-Skill | 2026-06-02 | Top-k should be a compatible set; 75.4% Hit@1 |
| [2604.05333](https://arxiv.org/abs/2604.05333) | Graph-of-Skills | 2026-04-07 | Pulling in prerequisite skills via a dependency graph (Personalized PageRank) |
| [2608.02880](https://arxiv.org/abs/2608.02880) | Field-Aware Skill Retrieval | 2026-08-03 | Per-field scores work better than one concatenated document |
| [2609.05824](https://arxiv.org/abs/2609.05824) | Diversity-aware routing (DSR) | 2026-09-05 | Diversity-aware reranking (determinantal point process) improves full coverage |
| **Generation / evolution** | | | |
| [2604.04804](https://arxiv.org/abs/2604.04804) | SkillX | 2026-04-06 | Builds skill knowledge bases automatically |
| [2603.04448](https://arxiv.org/abs/2603.04448) | SkillNet | 2026-02-26 | Repository of 600K+ skills; 5-dimension quality scoring |
| **Surveys / SoK** | | | |
| [2602.12430](https://arxiv.org/abs/2602.12430) · [2602.20867](https://arxiv.org/abs/2602.20867) · [2605.07358](https://arxiv.org/abs/2605.07358) | Surveys and SoK | Feb–May 2026 | Selection at scale is listed as an open challenge. The SoK finds self-generated skills can degrade performance |

## 4. Checking the Tavily deep-research report on routing

- **"Off-the-shelf retrievers score ≈70–73 NDCG@10 on SkillRet."** Only partly true. The best off-the-shelf model scores 70.26. The 73.54 figure belongs to SkillRouter-Emb, which was fine-tuned on skill data.
- **"LLM routing degrades beyond ~20 tools."** UNVERIFIED; the source is a blog. Anthropic's docs say 30–50 tools.
- **SkillsMP offers semantic search, and its MCP server refreshes hourly.** The semantic endpoint is gone (404 on 2026-09-24). The hourly refresh is UNVERIFIED.
- **The recommended cascade of shortlist sizes** is generic IR advice, not skill-specific evidence.

## Implications for Skill Atlas

1. **Offline build step** (`atlas index`, run in CI on every merge):
   - **Dedup.** Exact content hash, then near-duplicate clustering (~46% of the ecosystem is duplicated); keep one canonical entry per cluster plus `alternatives[]`.
   - **Index fields separately:**
     - `name` (weight 3)
     - `description` + `when_to_use` + tags (weight 2)
     - headings plus the first ~400 words of the body (weight 1)
     - 5–10 LLM-generated `example_queries` (weight 2)
     - an optional `not_for` field
   - **Body text for the source layer.** Pointer-only skills need their bodies crawled, since bodies carry the routing signal. Indexing third-party bodies is a licensing question.
   - **Boilerplate stoplist** from corpus IDF.
   - **Build artifacts:**
     - `router.sqlite`: FTS5 with the porter tokenizer, using `bm25(t, w…)` per-column weights ([FTS5](https://www.sqlite.org/fts5.html)). A prebuilt JSON inverted index is the equivalent for JavaScript runtimes.
     - Optional int8 vectors from `BAAI/bge-small-en-v1.5` (33M params, 384 dimensions, MIT) or `microsoft/harrier-oss-v1-270m` (640 dimensions, MIT; best small model on SkillRet), published as a release asset (~64 MB per 100K skills) rather than committed to git.
     - `router-lite.jsonl`.
2. **Ranking:**
   - Take BM25 top-50 and dense top-50 and fuse them with RRF (k=60; [Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)).
   - Penalize "black-hole" generic skills.
   - Apply MMR (maximal marginal relevance) to diversify and collapse duplicates.
   - Use trust tier and log(installs) only as small tie-breakers. Do **not** sort by popularity (the find-skills pattern).
   - Abstain when the top score is below a threshold τ.
   - The caller is an LLM, and LLM reranking was strongest on SRA-Bench: offer `rerank=agent`, returning 15 compact candidates.
3. **Query interfaces:**
   - **CLI:** `atlas find "<task>" [-k 5] [--layer curated] [--license permissive] [--json]`, plus `atlas show <id>`.
   - **MCP:** `search_skills(query, k=5, filters{layer, min_trust, license, tags, language})` and `get_skill(id, part)`. Keep the tool description modest; avoid "ALWAYS call first".
   - **Zero-install:** `router/SKILL.md` tells the agent to:
     - write 3–8 capability keywords plus a one-line imagined skill description ([2609.01642](https://arxiv.org/abs/2609.01642));
     - `grep -iE 'kw1|kw2' index/router-lite/*.jsonl | head -40`;
     - choose at most 3 skills.
   - **`router-lite` format:** one line per skill (`id, n, d≤200 chars, kw, tier, lic, install, url, digest`), about 250 bytes, sharded into files of ≤1 MB each. Include a curated-only shard small enough to read directly. Field names should follow Cloudflare's `/.well-known/agent-skills/index.json` (`name, description, url, digest`; [RFC v0.2.0](https://raw.githubusercontent.com/cloudflare/agent-skills-discovery-rfc/main/README.md)).
4. **Output contract.** Return k=5 by default: Anthropic's tool search defaults to 5, K-Dense to 3, and SkillsBench found focused skill sets do better. Each result includes:
   - `id`, `name`, `description`
   - `install` (e.g. `npx skills add owner/repo@skill`), `url`, `content_hash`
   - `trust_tier` (curated / verified-source / unverified), `license`
   - `alternatives_count`
   - `why_matched` (matched fields and terms, plus BM25, dense and RRF ranks)
   - `score`, plus a top-level `abstained` flag
   - a note to load only if needed and to confirm with the user before installing an unverified skill

   The router must return only IDs that exist in the index, because retrieval grounding cuts name hallucination from 40.8% to 3.2%.
5. **Evaluation plan:**
   - **Query set:** `eval/queries.jsonl` with at least 300 queries (growing to 1,000+).
     - Mix: 40% real requests, 40% generated from skill bodies with the name hidden (as SkillRouter did for training data), 20% multi-skill and no-answer queries.
     - Labels: multiple positives, including functional equivalents.
     - Never tune on synthetic queries alone.
   - **Metrics:** Recall@5 (primary), MRR@10, nDCG@10, Hit@1, precision and recall of abstention, duplicate rate in the top 5, p95 latency, and tokens returned.
   - **Runs:** report the curated and full pools separately, and at 1K, 10K and 100K skills to plot the routing-law curve. Baselines: grep-lite, BM25, dense, RRF, and RRF + agent rerank.
   - **Proposed targets.** These are my recommendations, not literature values:

     | Setting | Recall@5 | MRR@10 |
     |---|---|---|
     | BM25 ship gate | ≥0.75 | ≥0.55 |
     | Hybrid | ≥0.85 | ≥0.65 |
     | Stretch goal (SkillRet fine-tuned 0.6B level) | ≈0.82+ | – |

     Also: abstain correctly on ≥70% of no-answer queries; p95 latency under 100 ms (BM25) and under 500 ms (hybrid) on a laptop CPU.
6. **Risks:**
   - The **"SkillAtlas"** arXiv paper (2609.13353) is a name collision.
   - The "largest index" claims in AGENTS.md and `router/SKILL.md` are unsupported: the repo index is currently empty, while skills.sh lists over 600K skills.
   - A default router is a supply-chain chokepoint, so scanning and trust tiers must ship with it.
