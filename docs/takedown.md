# Takedown Process

This document describes the process for removing content from the Agent Skills Index.

## Overview

The Agent Skills Index respects intellectual property rights and takes content removal seriously. We provide a clear process for rights holders, security researchers, and other stakeholders to request content removal.

## Request Timeline

- **Acknowledgment:** We aim to acknowledge all takedown requests within 24 hours of receipt.
- **Processing:** Complete removal typically occurs within 3-5 business days, depending on the complexity of the request.
- **Emergency/Security:** Critical security issues receive expedited handling.

## How to Request a Takedown

### For Rights Holders and General Requests

1. **Submit an Issue:** Use the [Takedown Request issue template](../.github/ISSUE_TEMPLATE/takedown.yml) on GitHub.
2. **Provide Required Information:**
   - Content identifier (skill ID, repository URL, or content hash)
   - Your identity and relationship to the content
   - Contact email for follow-up
   - Detailed reason for the removal request
   - Supporting documentation (if applicable)
3. **Wait for Acknowledgment:** A maintainer will respond within 24 hours.
4. **Follow Up:** Respond to any clarifying questions promptly.

### For Security Issues

If you're reporting a security vulnerability in a skill:

1. **Submit a takedown request** using the issue template.
2. **Notify the upstream repository owner** directly (if safe to do so).
3. **Include CVE or vulnerability details** if available.

We will work with you to:
- Remove the vulnerable content from our index
- Notify relevant registries and downstream consumers
- Coordinate responsible disclosure with the upstream maintainer

## Technical Implementation

When a takedown request is approved, the maintainers will:

### 1. Execute the Takedown Command

```bash
atlas takedown <id|repo|hash> --reason "<brief description>"
```

This command:
- Adds the identifier to `policy/denylist.json`
- Retains a tombstone record in the index to prevent re-ingestion
- Removes active skill metadata and content

### 2. ID Persistence and Non-Reuse

- **Skill IDs are never reused.** Once a skill is removed, its identifier is permanently retired.
- This prevents confusion and ensures the removal is permanent.

### 3. Tombstone Records

Tombstone records in `index/skills.jsonl` contain:
- The skill ID
- A flag indicating the content was removed
- The removal timestamp
- No actual skill content or metadata

These tombstones ensure that:
- Crawlers don't re-ingest the removed content
- Downstream consumers can detect and clean up cached copies
- The audit trail is preserved

## Types of Takedown Requests

### Copyright/IP Rights Violations

For content that infringes on your intellectual property:
- Provide evidence of your rights (copyright registration, original work, etc.)
- Explain how the indexed content violates those rights
- Include any relevant DMCA or legal documentation

### License Violations

For content that violates its stated license terms:
- Identify the license terms being violated
- Explain how the indexing or distribution violates those terms
- Provide links to the license documentation

### Security Vulnerabilities

For skills containing malicious code or vulnerabilities:
- Describe the security issue in detail
- Provide CVE numbers or security advisories if available
- Indicate whether this is a 0-day or publicly disclosed issue

We will:
- Remove the content immediately upon verification
- Notify the upstream repository owner
- Alert relevant registries and skill distribution platforms
- Coordinate with the reporter on disclosure timing

### Privacy Concerns

For content that exposes personal information:
- Identify the specific information at risk
- Explain why it should not be public
- Provide evidence of harm or potential harm

### Malicious Content

For intentionally harmful or abusive content:
- Describe the nature of the harm
- Provide examples or evidence
- Indicate any affected parties

## Appeal Process

If your content was removed and you believe the removal was in error:

1. **Review the original takedown request** (linked in the removal notice).
2. **Submit a counter-notice** by opening a new issue titled "Counter-Notice: [Original Issue #]".
3. **Provide:**
   - Your contact information
   - Identification of the removed content
   - A statement under penalty of perjury that the removal was a mistake
   - Supporting evidence for reinstatement
4. **Wait for review:** We will evaluate counter-notices within 5-7 business days.

## Transparency

- All takedown requests are tracked via public GitHub issues (with sensitive information redacted as needed).
- The denylist (`policy/denylist.json`) is publicly visible (though it may omit detailed rationales for privacy or security reasons).
- We maintain statistics on takedown requests in our transparency reports.

## Legal Compliance

This process aligns with:
- DMCA takedown requirements (for U.S.-based content)
- GDPR right-to-erasure provisions (for EU personal data)
- General best practices for content moderation

## Contact

For urgent or sensitive takedown requests, you may also email the maintainers directly (see [`SECURITY.md`](../SECURITY.md) for contact information).

For questions about this process, open an issue with the "question" label.

---

**Last Updated:** 2026-09-24  
**Related Documentation:** [Inclusion Criteria](inclusion-criteria.md), [Contributing Guidelines](../CONTRIBUTING.md)
