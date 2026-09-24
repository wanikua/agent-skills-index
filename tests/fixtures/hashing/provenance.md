---
name: provenance-test
description: Test skill with provenance keys that should be stripped
local-path: /some/local/path
mintlify-proj: some-project
metadata:
  github-repo: owner/repo
  github-commit: abc123
  other-key: should-remain
---

# Provenance Test

This skill has provenance keys in frontmatter that should be removed.
