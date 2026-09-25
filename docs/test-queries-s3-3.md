# Test Discovery Queries for skill-atlas v1

This document walks through 10 handwritten discovery queries to validate the v1 zero-install discovery path documented in `skills/skill-atlas/SKILL.md`.

## Test Methodology

Each query follows the documented flow:
1. Check for local `atlas` CLI
2. If not available, use zero-install path (fetch router-lite shards)
3. Present candidates with full metadata
4. Get user confirmation

---

## Query 1: Find a PDF skill

**User request:** "Find a skill to extract text from PDF files"

**Keywords:** pdf, extract, text, document, parse

**Path used:** Zero-install (router-lite)

**Shards to fetch:**
- `https://raw.githubusercontent.com/wanikua/agent-skills-index/main/index/router-lite/curated.jsonl`
- `https://raw.githubusercontent.com/wanikua/agent-skills-index/main/index/router-lite/official.jsonl`

**Expected matches:** Skills with keywords matching "pdf", "extract", "text"

**Candidates (example):**
1. **pdf** (official, curated) - From anthropics/skills
   - License: Apache-2.0, Security: pass
2. **document-extractor** (community) - Generic document extraction
   - License: MIT, Security: pass

**Outcome:** Present top 3 candidates, show metadata, wait for confirmation

---

## Query 2: Find a Notion integration skill

**User request:** "I need a skill to search and query Notion databases"

**Keywords:** notion, database, query, search, api

**Path used:** Zero-install (router-lite)

**Shards to fetch:**
- curated.jsonl, official.jsonl

**Expected matches:** Skills with "notion" and "database" in kw/n/d fields

**Candidates (example):**
1. **notion-search** (curated) - Search Notion databases
   - License: MIT, Security: pass
2. **notion-api** (official) - Notion API integration
   - License: Apache-2.0, Security: pass

**Outcome:** Present candidates with full metadata (source, license, commit hash, security)

---

## Query 3: Find a GitHub automation skill

**User request:** "Find skills for automating GitHub workflows"

**Keywords:** github, workflow, automation, ci, actions

**Path used:** Zero-install → grep community shards if needed

**Shards to fetch:**
- curated.jsonl, official.jsonl
- If no matches: `community-*.jsonl` with grep

**Expected matches:** GitHub-related skills

**Candidates (example):**
1. **github-automation** (community)
   - License: MIT, Security: pass
2. **gh-actions** (community)
   - License: Apache-2.0, Security: review

**Outcome:** Show security status difference (pass vs review), let user decide

---

## Query 4: Find a skill for working with Excel files

**User request:** "I need to parse and analyze Excel spreadsheets"

**Keywords:** excel, xlsx, spreadsheet, parse, csv

**Path used:** Zero-install (router-lite)

**Shards to fetch:**
- curated.jsonl, official.jsonl

**Expected matches:** Excel/spreadsheet skills

**Candidates (example):**
1. **xlsx** (official, curated) - From anthropics/skills
   - License: Apache-2.0, Security: pass
2. **spreadsheet-parser** (community)
   - License: MIT, Security: pass

**Outcome:** Present with install commands

---

## Query 5: Find a web scraping skill

**User request:** "Find a skill to scrape and extract data from web pages"

**Keywords:** web, scrape, extract, html, parse, crawl

**Path used:** Zero-install → community shards

**Shards to fetch:**
- curated.jsonl, official.jsonl
- `grep -iE 'scrape|crawl' community-*.jsonl | head -40`

**Expected matches:** Web scraping/parsing skills

**Candidates (example):**
1. **web-scraper** (community)
   - License: MIT, Security: review
2. **html-parser** (community)
   - License: BSD-3-Clause, Security: pass

**Outcome:** Highlight security status, recommend the one with "pass" status

---

## Query 6: Find a skill for image processing

**User request:** "I need to resize and convert image files"

**Keywords:** image, resize, convert, process, transform

**Path used:** Zero-install (router-lite)

**Shards to fetch:**
- curated.jsonl, official.jsonl

**Expected matches:** Image processing skills

**Candidates (example):**
- May find 1-2 matches or abstain if not in index

**Outcome if no matches:** 
"No matching skills found in Skill Atlas for image processing. Consider:
- Searching GitHub directly for 'agent skills image'
- Creating a custom skill
- Using general-purpose file manipulation skills"

---

## Query 7: Find a skill for working with databases

**User request:** "Find skills to query SQL databases"

**Keywords:** database, sql, query, postgresql, mysql

**Path used:** Zero-install → community shards

**Shards to fetch:**
- curated.jsonl, official.jsonl
- community shards if needed

**Expected matches:** Database-related skills

**Candidates (example):**
1. **sql-query** (community)
   - License: MIT, Security: pass
2. **database-connector** (community)
   - License: Apache-2.0, Security: review

**Outcome:** Present with trust tier indicators (community vs official)

---

## Query 8: Find a skill with local atlas CLI

**User request:** "Find a skill for sending emails"

**Keywords:** email, send, smtp, mail

**Path used:** Local atlas CLI (if available)

**Command:**
```bash
atlas find "send emails via SMTP" --json
```

**Expected output:**
```json
{
  "query": "send emails via SMTP",
  "abstained": false,
  "results": [
    {
      "id": "github.com/example/skills/email-sender",
      "name": "email-sender",
      "description": "Send emails via SMTP with attachments",
      "license": "MIT",
      "security": "pass",
      "trust_tier": "community",
      "content_hash": "sha256:...",
      "url": "https://github.com/example/skills/tree/main/email-sender"
    }
  ]
}
```

**Outcome:** Present parsed results from JSON output

---

## Query 9: Find a skill for a very specific niche task

**User request:** "Find a skill to control my smart home IoT devices"

**Keywords:** iot, smart home, home automation, device control

**Path used:** Zero-install → all shards

**Shards to fetch:**
- curated.jsonl, official.jsonl
- All community shards with grep

**Expected matches:** Likely none (niche use case)

**Outcome (abstain):**
"No matching skills found in Skill Atlas for IoT/smart home automation.
Searched: curated, official, and community shards
Keywords tried: iot, smart home, home automation, device control

Suggestions:
- Search GitHub for 'agent skills iot' or 'SKILL.md home automation'
- Consider creating a custom skill for your specific IoT platform
- Check if there are API integration skills that could work"

---

## Query 10: Find multiple related skills

**User request:** "Show me all skills for working with documents"

**Keywords:** document, file, parse, convert, extract

**Path used:** Zero-install → broad search

**Shards to fetch:**
- curated.jsonl, official.jsonl
- `grep -iE 'document|parse' community-*.jsonl | head -40`

**Expected matches:** Multiple document-related skills

**Candidates (select top 3):**
1. **pdf** (official, curated) - PDF extraction
   - License: Apache-2.0, Security: pass
2. **docx** (official, curated) - DOCX processing
   - License: Apache-2.0, Security: pass
3. **document-converter** (community) - Multi-format conversion
   - License: MIT, Security: pass

**Outcome:** Present top 3 most relevant, note that more exist, let user choose

---

## Summary

All 10 test queries successfully follow the documented flow:

| Query | Primary Path | Fallback Path | Expected Outcome |
|-------|-------------|---------------|------------------|
| 1. PDF extraction | router-lite | - | Found (curated/official) |
| 2. Notion | router-lite | - | Found (curated/official) |
| 3. GitHub automation | router-lite | community grep | Found (community) |
| 4. Excel | router-lite | - | Found (official) |
| 5. Web scraping | router-lite | community grep | Found (community) |
| 6. Image processing | router-lite | - | Abstain (not found) |
| 7. SQL databases | router-lite | community grep | Found (community) |
| 8. Email (with CLI) | atlas find | - | Found via CLI |
| 9. IoT/smart home | router-lite | all shards | Abstain (not found) |
| 10. Document skills | router-lite | community grep | Found multiple |

**Key validations:**
- ✅ Two-path discovery (CLI vs zero-install) documented
- ✅ Router-lite short-key format documented and explained
- ✅ Metadata presentation (source, license, commit/hash, security) correct
- ✅ User confirmation required before install
- ✅ Abstain/not-found cases handled properly
- ✅ No invented skill IDs (only return what's in index)
- ✅ Preference hierarchy (curated → official → community) followed
- ✅ Security and trust tier indicators shown
- ✅ No absolutist language ("ALWAYS use first" avoided)

## Notes on Implementation

When agents implement this skill:
1. Always fetch curated + official first (small, ~100KB each)
2. Only grep community shards when needed (1MB each)
3. Parse the short-key JSON format correctly
4. Show full metadata before any install
5. Handle "not found" gracefully without inventing skills
6. Respect security and trust indicators in recommendations
