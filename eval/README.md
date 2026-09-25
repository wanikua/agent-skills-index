# Evaluation Datasets for Skill Atlas

This directory contains calibration and evaluation datasets for the deduplication (S2-3) and security scanning (S2-4) tasks defined in `docs/PLAN.md`.

## Files

### `dedup-pairs.jsonl`

Labeled pairs of Agent Skills for calibrating and evaluating the MinHash-based near-duplicate detection system.

**Format:** One JSON object per line.

**Fields:**
- `pair_id` (integer): Unique identifier for this pair
- `skill_a` (object): First skill with `name`, `description`, and `content` fields
- `skill_b` (object): Second skill with `name`, `description`, and `content` fields
- `label` (string): One of:
  - `"exact-duplicate"` — Identical or near-identical content (content_hash would match)
  - `"near-duplicate"` — Paraphrased, minor edits, or functionally equivalent (human would consider duplicates)
  - `"not-duplicate"` — Different skills, possibly overlapping vocabulary but distinct functionality
- `notes` (string): Human-readable explanation of the label

**Count:** 300 pairs minimum

**Coverage:**
- Exact duplicates: Anthropics skills (pdf/docx/excel/pptx) and their aggregator copies
- Near duplicates: Paraphrases, synonym substitutions, minor structural changes
- Not duplicates: Different skills with overlapping domain terms (e.g., PDF extraction vs PDF generation, Excel vs CSV)

**Usage (S2-3):**
The MinHash deduplication algorithm should be tuned using this dataset:
- Similarity threshold calibration (e.g., ≥0.90 for near-duplicate, ≥0.99 for mirror)
- MinHash parameters (`num_perm`, LSH threshold)
- Text preprocessing (normalization, tokenization)

Target metrics (from PLAN.md S2-3):
- Precision ≥ 0.95
- Recall ≥ 0.85

### `security-samples.jsonl`

Labeled security samples for calibrating IOC (Indicator of Compromise) detection rules and evaluating security scanners.

**Format:** One JSON object per line.

**Fields:**
- `sample_id` (integer): Unique identifier
- `description` (string): Human-readable description of the sample
- `text` (string): Sample text content (SKILL.md excerpt, command, or code pattern)
- `risk_level` (string): One of `"low"`, `"medium"`, `"high"`
- `ioc_patterns` (array of strings): List of IOC patterns this sample should match (empty for clean samples)
- `status` (string): Expected S2-4 security status:
  - `"pass"` — Clean, no issues
  - `"review"` — Requires human review (e.g., legitimate but sensitive capabilities)
  - `"warn"` — Warning-level findings (e.g., insecure patterns, suspicious but not definitively malicious)
  - `"malicious"` — Clear malicious intent
- `notes` (string): Explanation

**Count:** 100 samples minimum

**Coverage:**
- Known malicious patterns:
  - `curl|sh`, `wget|bash` (remote code execution)
  - `base64|bash` (obfuscation)
  - Credential theft (`~/.ssh`, `~/.aws/credentials`, `$GITHUB_TOKEN`)
  - Data exfiltration (POST sensitive files to external endpoints)
  - Reverse shells, keyloggers, ransomware indicators
- Suspicious but contextual:
  - System file access (`/etc/passwd`, `/etc/shadow`)
  - Network scanning, packet capture
  - Privilege escalation (`sudo`, registry Run keys)
- Legitimate patterns that should not trigger:
  - Normal file I/O
  - Standard API calls
  - Documented features (screenshots, VPN, encryption)
- Vulnerability patterns:
  - SQL injection, NoSQL injection
  - Command injection, path traversal
  - XSS, CSRF, XXE, insecure deserialization

**IMPORTANT:** This file contains **NO executable payloads, NO real malware, NO exploit code**. All samples are:
- Harmless text patterns
- Descriptive strings
- Example command syntax
- Placeholder domains (example.com, evil.com, attacker.com)

**Usage (S2-4):**

#### Source Index Layer (all skills)
Run lightweight static checks + IOC matching:
- Match against `ioc_patterns` list
- Assign `security.status` based on findings
- Tag with `security.risk_level` and matched capabilities

Expected behavior:
- `status == "malicious"` → samples with clear attack indicators
- `status == "warn"` → samples with `risk_level == "high"` and suspicious patterns
- `status == "review"` → samples with sensitive capabilities but legitimate use cases
- `status == "pass"` → clean samples with no IOC matches

#### Curated Layer (strict gate)
Requires two-engine scanning + human review:
- Cisco `skill-scanner --policy strict` + SkillSpector
- No unresolved HIGH/CRITICAL findings
- Human review for all MEDIUM findings

Samples with `status == "malicious"` or high-risk IOC patterns must be rejected.

## Validation

Run `pytest tests/test_eval.py` to validate:
- Files exist and parse as valid JSONL
- Minimum counts met (≥300 pairs, ≥100 security samples)
- Required fields present
- Labels in allowed sets
- No duplicate pair_ids or sample_ids

## Maintenance

These datasets are **ground truth** for S2-3 and S2-4. When updating:
1. Add new pairs/samples to cover edge cases found in production
2. Re-run validation tests
3. Document any schema changes in this README
4. Update target metrics in PLAN.md if thresholds change

Do not modify labels without careful consideration — these are the reference standard for tuning algorithms.

## Schema Version

Version: 1.0.0 (2026-09-24)

Compatible with:
- PLAN.md S2-3 (MinHash deduplication)
- PLAN.md S2-4 (Security scanning)
