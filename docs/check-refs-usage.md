# External Reference Checking (S2-5)

## Overview

The `atlas check-refs` command validates external references in Agent Skills to protect against **SkillJacking** attacks and broken dependencies.

### What is SkillJacking?

SkillJacking occurs when:
1. A skill repository owner deletes their account
2. An attacker registers the same username
3. The attacker gains control over all skills pointing to that username

This protection **automatically marks skills from deleted owners as dangling** and triggers takedown.

## Quick Start

```bash
# Install dependencies (includes dnspython for DNS checks)
pip install -e .[dev]

# Check external references in crawled skills
atlas check-refs

# Check specific source
atlas check-refs --source anthropic-skills

# Check with owner verification (slower, makes network calls)
atlas check-refs --check-owners --verbose

# Build index with reference checking enabled
atlas build --check-refs
```

## What It Checks

### GitHub Repositories
- **Method**: `git ls-remote` (no authentication required)
- **Checks**: Repository exists and is accessible
- **Example**: `https://github.com/anthropics/skills`

### GitHub Owners
- **Method**: `git ls-remote` to owner's repositories
- **Checks**: Owner/organization account still exists
- **Critical**: If source repo owner is deleted, all skills are marked `dangling`

### Domains
- **Method**: DNS A/AAAA record resolution
- **Checks**: Domain resolves to an IP address
- **Example**: `https://api.openai.com`

### npm Packages
- **Method**: npm registry JSON API
- **Checks**: Package exists on registry.npmjs.org
- **Example**: `npm install lodash` or `@anthropic/sdk`

### PyPI Packages
- **Method**: PyPI JSON API
- **Checks**: Package exists on pypi.org
- **Example**: `pip install requests`

## Output

### Skill with Dangling References

```
⚠️  Dangling refs in skills/test/SKILL.md:
  - deleted-owner/deleted-repo
  - nonexistent-package-12345
  - unresolvable-domain.invalid
```

### Source with Deleted Owner

```
Checking source repository owners...
  ⚠️  DELETED OWNER: https://github.com/deleted-owner/repo

⚠️  WARNING: 1 source(s) have deleted owners!
These skills should be marked as 'dangling' and taken down.
```

## Integration with Build

When `atlas build --check-refs` is used:

1. **Pre-build check**: Validates all source repository owners
2. **Per-skill check**: Extracts and validates references from each skill
3. **Status marking**: 
   - Skills with broken refs → `status: "dangling"`
   - Skills from deleted owners → `status: "dangling"` + `status_reason: "source_owner_deleted"`
4. **Metadata**: Stores check results in `security.external_refs`

## Configuration

### Timeout

Default timeout is 10 seconds per check. Adjust with:

```bash
atlas check-refs --timeout 30
```

### Offline Testing

All network calls are mockable. Tests use `unittest.mock` to provide deterministic results without making real network calls.

```python
from tools.atlas import check_refs

# Create mock checker for testing
checker = check_refs.ReferenceChecker()
# All methods (check_github_repo, check_domain, etc.) can be mocked
```

## Performance

Reference checking adds network overhead:

- **GitHub repo check**: ~200-500ms per repo
- **Domain check**: ~50-200ms per domain  
- **Package check**: ~100-300ms per package
- **Owner check**: ~200-500ms per source

**Recommendation**: 
- Use `atlas check-refs` as a separate validation step
- Enable `--check-refs` in `atlas build` for daily refresh workflow
- Do NOT enable for every local build during development

## Schema Changes

Skills now include:

```json
{
  "status": "active" | "dangling" | "removed" | "quarantined",
  "status_reason": "source_owner_deleted" | null,
  "security": {
    "external_refs": [
      {
        "type": "github_repo" | "domain" | "npm_package" | "pypi_package",
        "reference": "owner/repo",
        "exists": true | false,
        "error": "error message" | null
      }
    ]
  }
}
```

## Testing

Run the test suite:

```bash
# All check-refs tests (28 tests)
pytest tests/test_check_refs.py -v

# Specific test categories
pytest tests/test_check_refs.py::TestReferenceExtractor -v
pytest tests/test_check_refs.py::TestReferenceChecker -v
pytest tests/test_check_refs.py::TestFixtures -v
```

All tests are fully mocked and do not require network access.

## Troubleshooting

### "Timeout" errors

Increase timeout or check network connectivity:

```bash
atlas check-refs --timeout 30 --verbose
```

### False positives

Some repos may be private or require authentication. The checker conservatively assumes they exist if the error is ambiguous.

### DNS failures

If DNS is unreliable, domains may be incorrectly marked as dangling. Consider retrying or using a different DNS resolver.

## Implementation Details

See:
- `tools/atlas/check_refs.py` - Core implementation
- `tests/test_check_refs.py` - Test suite with fixtures
- `docs/PLAN.md` §S2-5 - Specification

## Related Commands

- `atlas crawl` - Crawl skills from sources
- `atlas build` - Build index (use `--check-refs` to enable checking)
- `atlas validate` - Validate index schema and data

## Future Enhancements

- Retry logic with exponential backoff
- Caching of check results (by content hash)
- Parallel checking for better performance
- Integration with S2-4 security scanning
- Automated takedown workflow (S5-5)
