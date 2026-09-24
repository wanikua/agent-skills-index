# Security & Quality Gates for Skill Atlas: Findings (2026-09-24)

Deep-research leads were checked against primary sources. Anything I could not trace to a primary source is marked **UNVERIFIED**.

## 1. Incidents (chronological)

| Date (2026) | Incident | Key facts |
|---|---|---|
| Feb 1 – Feb 16 | **ClawHavoc** on ClawHub (OpenClaw) | Koi audited all 2,857 ClawHub skills and found 341 malicious, 335 of them from one campaign. The lure was a fake "Prerequisites" section: a password-protected ZIP on Windows ("to evade antivirus scanning"), and on macOS a glot.io script piping base64 to bash, fetching from 91.92.242.30 and delivering Atomic macOS Stealer (AMOS). By Feb 16 the count was 824 malicious out of 10,700+ skills. https://www.koi.ai/blog/clawhavoc-341-malicious-clawedbot-skills-found-by-the-bot-they-were-targeting (now redirects; read via Tavily's cache) |
| Feb | Antiy CERT final tally | 1,184 malicious skills across 12 publisher accounts. Reported via OWASP AST10, **UNVERIFIED** at primary. https://owasp.github.io/www-project-agentic-skills-top-10 |
| Feb | Publish bar at ClawHub | The only publishing requirement was a GitHub account at least one week old. **UNVERIFIED** (secondary source only). https://www.termdock.com/en/blog/clawhub-malicious-skills-incident |
| Feb 7 | OpenClaw + VirusTotal | Deterministic ZIP, SHA-256, VT lookup and Code Insight (Gemini). Benign is auto-approved, suspicious is warned, malicious is blocked; daily re-scan. OpenClaw: "not a silver bullet". https://openclaw.ai/blog/virustotal-partnership |
| Feb 17 | Clinejection (adjacent: agent CI) | A prompt injection in an issue title steered claude-code-action into cache poisoning, which stole the npm token. `cline@2.3.0` was then published with `npm install -g openclaw@latest`. https://adnanthekhan.com/posts/clinejection |
| Feb–May | Evasive skills that survived VT + ClawScan | Unit 42 found 5 unblocked skills using: file padding past scanner size limits; paste-site lures (rentry.co) that got "Pass"; affiliate injection via a remote `referrals.json`; and agents pooling SOL for front-running. The accounts were banned. https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk |
| Jun 3 | Trail of Bits scanner bypass | Bypassed ClawHub (VT plus a GPT‑5.5 guard), Cisco skill-scanner, and skills.sh's Gen, Socket and Snyk. Techniques: 100,000 prepended newlines to force truncation, instructions hidden in a `.docx`, poisoned `.pyc` bytecode, and prompt-injecting the LLM judge. Three of the four took under an hour. https://blog.trailofbits.com/2026/06/03/the-sorry-state-of-skill-distribution |
| Jun 24 / Jul 2 | Air Security | 17,822 skills (12.4% of GitHub skills, 6.7M installs) fetch external instructions from untrusted sources. **SkillJacking**: 925 skills serving about 134K agents rest on hijackable dependencies (deleted GitHub accounts, unregistered packages, expired domains, freed cloud-app slots). Air took over `seedance2-api` (11,483 installs) by re-registering its deleted owner. https://www.air.security/blog-posts/skilljacking |
| Jul 20 | Island "AgentBaiting" | About 7,600 malicious GitHub repos, 800+ of them posing as Skills or MCP servers. They appeared **600+ times across public AI registries/catalogs**. https://www.island.io/blog/agentbaiting-how-800-fake-ai-skills-and-mcp-servers-delivered-malware |

**Aggregators are an attack surface** (the same model as our source layer):
- 157 confirmed-malicious skills were found via the GitHub aggregators skills.rest and skillsmp.com (https://arxiv.org/abs/2602.06547).
- 121 listed skills point at 7 GitHub repos that anyone could re-register (https://arxiv.org/abs/2603.16572).

## 2. Empirical studies

| Study | Corpus | Findings |
|---|---|---|
| Agent Skills in the Wild (arXiv 2601.10338) https://arxiv.org/abs/2601.10338 | 42,447 collected, 31,132 analyzed | See detail below the table. |
| Snyk ToxicSkills tech report (2605.28588) https://arxiv.org/abs/2605.28588 | 3,984 skills (ClawHub + skills.sh) | 13.4% had a critical issue and 36.82% had any flaw. 76 malicious payloads were confirmed, 8 still live at publication. 100% of the confirmed malicious skills contained malicious code and 91% also used prompt injection. Eight policies: Prompt Injection, Malicious Code, Suspicious Downloads (CRITICAL); Improper Credential Handling, Secrets (HIGH); Third-Party Content Exposure, Unverifiable Dependencies/remote prompt, Direct Money Access (MEDIUM). |
| "Do Not Mention This to the User" (2602.06547) https://arxiv.org/abs/2602.06547 | 98,380 skills | 157 confirmed malicious, carrying 632 vulnerabilities across 13 techniques (about 4 per skill). **One actor accounts for 54.1%** through templated brand impersonation. All 157 were removed after disclosure. |
| Context Matters (2603.16572) https://arxiv.org/abs/2603.16572 | 238,180 skills | Marketplace scanners flag 46.8% (ClawHub), 23% (skills.sh) and 6% (SkillsDirectory). Adding repository context leaves only 15 of 2,887 flagged cases (0.52%) suspicious. **Large false-positive problem.** |
| SkillSieve (2604.06550) https://arxiv.org/abs/2604.06550 | 49,592 ClawHub skills | Three layers: regex/AST/metadata triage, then 4 LLM sub-tasks, then a 3-model jury. F1 0.929 (P 0.912, R 0.945) at $0.006 per skill. |
| Cloak and Detonate (2607.02357) https://arxiv.org/abs/2607.02357 | 8 scanners, 1,613 malicious skills | Self-extracting packing bypasses every scanner more than 90% of the time; obfuscation bypasses most static scanners more than 80% of the time. A sandbox plus taint analysis ("SkillDetonate") detects 97% at 2% FPR. |
| DDIPE (2604.03081) https://arxiv.org/abs/2604.03081 | 1,070 adversarial skills | Payloads hidden in doc code examples reach 11.6–33.5% bypass. Static analysis catches most; 2.5% evade both static analysis and model alignment. |
| Under the Hood of SKILL.md (2605.11418) https://arxiv.org/abs/2605.11418 | Real ClawHub skills | Text triggers reach the embedding-retrieval Top-10 up to 80% of the time; description framing wins selection in 77.6% of trials; evasion avoids blocking in 36.5–100%. |
| Skills Are Not Islands (2607.01136) https://arxiv.org/abs/2607.01136 | 1.43M skills | Only 11.25% declare a license and 20.12% a version. 1.40% have dependency fields, yet more than 30% actually carry dependencies. |

**Detail for Agent Skills in the Wild (2601.10338):**
- 26.1% of skills have at least one vulnerability. Data exfiltration appears in 13.3% and privilege escalation in 11.8%; 5.2% show likely-malicious high-severity patterns.
- Skills that bundle scripts are 2.12× more likely to be vulnerable.
- The static regex stage alone scored P 71.4% / R 91.2%; the hybrid static+LLM pipeline scored P 86.7% / R 82.5%.
- Taxonomy of 14 patterns in 4 groups:
  - Prompt injection: P1 instruction override, P2 hidden instructions, P3 exfiltration commands, P4 behavior manipulation.
  - Exfiltration: E1 external transmission, E2 env-var harvesting, E3 filesystem enumeration, E4 context leakage.
  - Privilege escalation: PE1 excessive permissions, PE2 sudo, PE3 credential access.
  - Supply chain: SC1 unpinned dependencies, SC2 external script fetching, SC3 obfuscation.

## 3. Scanners

| Tool | Detects / method | License | CI command | Caveats |
|---|---|---|---|---|
| **Cisco skill-scanner** https://github.com/cisco-ai-defense/skill-scanner | YAML + YARA-X rules, `.pyc` integrity, shell-pipeline taint, Python AST dataflow. Optional LLM, meta-analyzer, VirusTotal and Cisco AI Defense. Also `--check-overlap` (cross-skill overlap) and `--use-trigger` (vague descriptions). | Apache-2.0 (PyPI `cisco-ai-skill-scanner` 2.1.0) | `skill-scanner scan-all ./skills --recursive --policy strict --fail-on-severity high --format sarif --output results.sarif`; also a pre-commit hook | Self-reported: P 99.16% / R 31.43% on its dev set, but **P 60.75% / R 7.75% / FPR 7.71%** on a held-out split. "No findings ≠ no risk." |
| **NVIDIA SkillSpector** https://github.com/nvidia/skillspector | 71 patterns in 17 categories; static analysis, optional LLM, OSV lookups. Used by ClawHub and NVIDIA. | Apache-2.0 | `skillspector scan ./skill --no-llm --format sarif --output r.sarif` | Build from source or Docker; `--baseline` suppresses known false positives. |
| **Snyk Agent Scan** https://github.com/snyk/agent-scan | LLM judges plus rules (the ToxicSkills policies) | Apache-2.0 (PyPI `snyk-agent-scan` 0.6.4) | `uvx snyk-agent-scan@latest path/SKILL.md --ci` (needs `SNYK_TOKEN`) | **Sends skill content to Snyk's API.** "Large scale scanning" on the standard API "is considered abuse"; registries must request a designated API. |
| **VirusTotal / Code Insight** https://openclaw.ai/blog/virustotal-partnership | Hash reputation plus LLM code summary | Commercial API | Via Cisco's `--use-virustotal` | Weak on natural-language attacks. |
| **skills.sh audits** https://vercel.com/changelog/automated-security-audits-now-available-for-skills-sh | Gen, Socket and Snyk; 60,000+ skills audited | Service | n/a | Malicious skills are hidden from search; the CLI shows risk before install. |
| **ClawHub audit** https://github.com/openclaw/clawhub/blob/main/docs/security-audits.md | SkillSpector + Tencent A.I.G + ClawScan. Checks whether metadata and actual behavior are **coherent**. | n/a | n/a | Rejects `.pyc/.pyo/.pyd` files. |

**False positives.**
- Repository context cuts scanner flags by about 99% (https://arxiv.org/abs/2603.16572).
- Anthropic's own Office skills compile embedded C at runtime, which scanners rate MEDIUM/LOW (https://blog.trailofbits.com/2026/06/03/the-sorry-state-of-skill-distribution).

## 4. Recommended registry controls

1. **Treat scanner output as triage, not certification.** Trail of Bits: "No amount of scanning or LLM analysis can reliably detect malicious content… use curated marketplaces… pin to specific versions." https://blog.trailofbits.com/2026/06/03/the-sorry-state-of-skill-distribution
2. **Scan the whole file tree and fail closed.** Include hidden files, not only the files SKILL.md references. Allowlist file types; reject binaries, archives, `.docx` and bytecode (ClawHub does). Cap file sizes, and treat a truncated scan as a failure rather than a pass.
3. **Prompt-injection and malware heuristics** for the recall stage (SkillScan Table 4 plus the IOCs above):
   - Code patterns: `curl…|…sh`, `base64…|bash`, `eval(`/`exec(`, `base64.b64decode…exec`, `os.environ[`, `requests.post(…http`, `sudo`, `chmod [0-7]{3,4}`.
   - Instruction phrases: "ignore previous instructions", "send to <URL>", `~/.ssh`, `/etc/passwd`.
   - Delivery indicators: raw-IP URLs, paste sites (glot.io, rentry.co), password-protected ZIPs, "Prerequisites" download blocks, invisible Unicode characters, XML tags in `description` (Anthropic forbids them).
4. **Inventory external references and re-check them.** Confirm that every GitHub owner, domain and package a skill references still exists; flag runtime-fetched instructions and unpinned dependencies (SkillJacking; OWASP AST05/AST07). https://owasp.github.io/www-project-agentic-skills-top-10
5. **Provenance.**
   - Pin the commit SHA and store per-file hashes. Nesbitt: most loaders treat "version" as "default branch at fetch time" and record "name and version and not the bytes". https://nesbitt.io/2026/06/03/skills-registry-threat-models.html
   - Add a directory identity using Gen's **Skill ID**: git-tree-style SHA-256 with NFC paths, forward slashes and the wrapper directory stripped. https://github.com/gendigitalinc/skill-id-standard
   - Sign curated releases with **OpenSSF model-signing** (Sigstore/DSSE; Apache-2.0), as NVIDIA does for skills: `model_signing verify certificate SKILL_DIR --signature skill.oms.sig …`. https://developer.nvidia.com/blog/nvidia-verified-agent-skills-provide-capability-governance-for-ai-agents, https://github.com/sigstore/model-transparency
6. **Separate labels and takedown actions.**
   - ClawHub splits **audit status** (Pass / Review / Warn / Malicious / Pending / Error) from **risk level** (Low / Medium / High, meaning "blast radius"). https://github.com/openclaw/clawhub/blob/main/docs/security-audits.md
   - Keep yank, remove and ban separate; tombstone deleted names. ClawHub moderation has reports, holds, hidden/quarantined/revoked states and appeals. https://github.com/openclaw/clawhub/blob/main/docs/moderation.md
7. **Re-scan continuously.** OpenClaw re-scans daily; Air: "vetted continuously, not only when installed."

## 5. Quality

**Evaluations.**
- SkillsBench (87 tasks, 18 configurations): curated skills raise pass rate from 33.9% to 50.5%.
- Compact, standard-length skills (+19.0 and +21.5 pp) beat comprehensive documentation (+0.7 pp).
- **Self-generated skills (written with skill-creator) score *below* the no-skill baseline on all three harnesses tested.**
- https://arxiv.org/abs/2602.12670

**Routable descriptions.**
- Spec limits: `name` 1–64 characters, `[a-z0-9-]`, must match its directory; `description` 1–1024 characters. Recommended: body under 5,000 tokens and SKILL.md under 500 lines. https://agentskills.io/specification
- Anthropic: write in the third person, say both *what* the skill does and *when* to use it, no XML tags, no reserved words ("anthropic", "claude"). https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- agentskills.io's trigger eval: about 20 queries (8–10 should-trigger, 8–10 near-miss should-not), 3 runs each, pass threshold 0.5, 60/40 train/validation split. https://agentskills.io/skill-creation/optimizing-descriptions
- Caution: description text can be adversarially optimized for retrieval (see 2605.11418), so ranking must not rely on the description alone.

**Smells.**
- Over 99% of SKILL.md files contain at least one smell. https://arxiv.org/abs/2607.01456
- Statically detectable ones:
  - body longer than 5,000 words;
  - name longer than 64 characters;
  - description longer than 1,024 characters;
  - XML tags in the description;
  - backslash paths.

**Spam / AI-generated content.**
- Text detectors are unreliable. OpenAI's classifier caught 26% of AI-written text with a 9% false-positive rate and was withdrawn. https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/
- Use behavioral and cluster signals instead:
  - Bulk or bot accounts: VoltAgent excluded 4,065 spam, 1,040 duplicate-name and 851 low-quality ClawHub skills. https://github.com/VoltAgent/awesome-openclaw-skills
  - Templated reposting: 46.3% of 40,285 skills share a normalized name, and some names appear more than 100 times. https://arxiv.org/abs/2602.08004
  - Single-actor saturation (54.1%, above).

**Duplicate detection.**
- Evidence:
  - Reuse is mostly copying: 1,841 of 2,462 reused skills are at 0.99 or higher longest-common-subsequence body similarity. https://arxiv.org/abs/2607.00911
  - 34,956 of 54,980 scripts appear in multiple skills (2601.10338).
  - Embeddings of name+description (bge-m3) "do not reliably separate true duplicates", because the descriptions are short and template-derived (2602.08004).
- Algorithms:
  - MinHash beats SimHash (P 0.959 / R 0.942 vs 0.904 / 0.732, and roughly 55× faster). https://github.com/ChenghaoMou/text-dedup
  - FineWeb: 5-grams, 112 hashes in 14 bands × 8 rows (catches 92% of pairs at 0.8 similarity). https://arxiv.org/abs/2406.17557
  - Lee et al.: 5-grams, then confirm candidates with edit similarity above 0.8. https://arxiv.org/abs/2107.06499
  - Embedding dedup works on a cosine ≥ 1−ε rule. https://arxiv.org/abs/2303.09540

**Proposed dedup pipeline.** The thresholds are my proposal; calibrate them on about 300 labeled pairs.
1. **Exact.** `content_hash` = SHA-256 of normalized SKILL.md: strip the BOM, NFC, LF line endings, trim trailing whitespace, frontmatter keys sorted. Also compute `skill_id` (Gen Skill ID) over the whole tree.
2. **Near-duplicate.** Use `datasketch` (MIT): MinHash LSH over word 5-grams of the body, `num_perm=128`, LSH threshold 0.7. Confirm with an LCS/edit ratio: ≥0.90 means `near_duplicate_of`; ≥0.99 means `mirror_of`. Bodies under about 80 words go to exact matching only, because MinHash is noisy on short text.
3. **Semantic.** Embed the body and cluster at cosine ≥0.92 into `alternatives` for the router. **Never auto-reject** on this signal.
4. **Canonical choice.** Prefer the official publisher, then the earliest commit, then the upstream that others copied from.

## 6. Implications for Skill Atlas

**The main risk is our source layer.** It aggregates GitHub pointers, the same model through which 157 malicious skills and 600+ AgentBaiting listings reached agents. `AGENTS.md` tells agents to "Fetch from source_repo + source_path", so every pointer is effectively an install recommendation.

**SOURCE layer: minimal, automated, runs on every entry.**
1. Pin `source_commit` (a SHA, never a branch). The URL must resolve and the owner account must exist; a missing owner is marked `dangling` and delisted (SkillJacking).
2. Spec lint with `skills-ref validate`.
3. Offline static scan: Cisco core analyzers or `skillspector --no-llm`. Record the findings; exclude an entry only on:
   - a known IOC (VT malicious hash, ClawHavoc C2 or paste-site patterns);
   - an upstream "Malicious" verdict from ClawHub or skills.sh;
   - an exact-hash match to a skill we already blocked.
   Label everything else; scanner FP rates run 6–47%.
4. Collapse exact-hash mirrors.
5. Weekly re-scan.

**CURATED layer: hard gates.** Curated must pass everything the source layer does, plus:
1. The existing license allowlist.
2. **Two engines** (Cisco `--policy strict` with LLM, plus SkillSpector): zero unresolved HIGH/CRITICAL, and human review of every MEDIUM for metadata/behavior coherence.
3. File-type allowlist (text only: `.md`, `.py`, `.sh`, `.js`, `.ts`, `.json`, `.yaml`, `.txt`); no binaries, archives, bytecode, Office files or hidden files. Size caps: 1 MB per file, SKILL.md ≤5,000 words. A truncated scan means reject.
4. No instructions fetched at runtime and no `curl|bash`. Any external dependency must be pinned with hashes, or on an allowlisted domain.
5. Description quality:
   - third person, what + when, ≤1,024 characters, no XML;
   - no statically detectable smells;
   - a trigger eval of ≥85% on 20 queries (proposed threshold).
6. No near-duplicate of an existing curated skill unless it replaces that skill as the canonical one.
7. Provenance:
   - SHA pin, `content_hash` and `skill_id`;
   - the curated directory signed with `model_signing` (Sigstore) at release;
   - two maintainer approvals.
8. Takedown SLA: hide within 24 hours of a credible report, publish a tombstone and never reuse the id.

**Proposed fields for `index/schema.md`.** `security.status` answers "what should you do?"; `security.risk_level` answers "how much power does this skill have?".

```json
"provenance": {"source_commit":"<sha40>","content_hash":"sha256:…","skill_id":"sha256:…",
  "signature":{"type":"sigstore-model-signing","bundle":"curated/<id>/skill.oms.sig"},"owner_status":"ok|dangling"},
"security": {"status":"pass|review|warn|malicious|pending|error",
  "risk_level":"low|medium|high",
  "capabilities":["network","shell","credentials","fs-write","external-instructions","money"],
  "scans":[{"engine":"cisco-skill-scanner","version":"2.1.0","policy":"strict","commit":"<sha>",
            "ran_at":"2026-09-24T00:00:00Z","max_severity":"medium","counts":{"critical":0,"high":0,"medium":1},
            "taxonomy_refs":["SC2","AST05"]}],
  "external_refs":[{"kind":"github|domain|package","target":"…","state":"ok|dangling|unpinned"}],
  "upstream_verdicts":{"clawhub":"Pass","skills_sh":"…"},
  "takedown":{"state":"none|hidden|quarantined|revoked","reason":"…","date":"…"}},
"quality": {"spec_valid":true,"smells":["LSB"],"description_chars":212,"body_words":1840,
  "duplicate_of":null,"near_duplicate_of":null,"alternatives_cluster":"c-0412"}
```

Map `taxonomy_refs` to OWASP AST10 and SkillScan codes so labels survive cross-registry reuse. No bulk Snyk scanning without the designated API.
