# Contributing to Agent Skills Index

Thank you for your interest in contributing to the Agent Skills Index! This document outlines how to participate in this project.

## General Principles

**Human Review is Required:** We prioritize human-reviewed contributions. All submissions—whether written by humans or assisted by AI—must be carefully reviewed by a human before being submitted.

**AI-Generated PRs:** If you use AI assistance to generate a pull request, you must:
1. Thoroughly review all generated content for accuracy and quality
2. Verify that the changes align with our inclusion criteria and policies
3. Test any code changes locally
4. Clearly indicate in your PR description that AI was used and describe your review process

We do not accept automated or bulk PRs that have not been carefully reviewed by a human maintainer.

## How to Contribute

### Suggesting a New Skill Source

If you've found a repository containing agent skills that should be indexed:

1. **Check if it's already included:** Search the `sources/` directory and `index/sources.json` to see if the source is already tracked.
2. **Review our criteria:** Read [`docs/inclusion-criteria.md`](docs/inclusion-criteria.md) to ensure the source meets our standards.
3. **Open an issue:** Use the "Add Skill Source" issue template to propose the addition.
4. **Wait for review:** The maintainers will evaluate the source and provide feedback.

Do not submit a pull request directly adding a source without prior discussion via an issue.

### Reporting Issues

- **Bugs:** Use the "Bug Report" issue template to describe any technical issues.
- **Takedown Requests:** If you believe content should be removed (for copyright, security, or other reasons), use the "Takedown Request" issue template. We aim to acknowledge all takedown requests within 24 hours.

### Improving Documentation

Documentation improvements are welcome! Please:

1. Fork the repository
2. Create a branch for your changes
3. Make your edits with clear commit messages
4. Submit a pull request with a description of your changes

### Contributing to Curated Content

Changes to the `curated/` directory (featured skills, collections) require owner approval. Please:

1. Open an issue first to discuss your proposed changes
2. Wait for maintainer feedback before submitting a PR
3. Ensure your curated content follows our quality standards

### Contributing Code

For changes to tooling (`tools/`), schema, or infrastructure:

1. **Discuss first:** Open an issue to discuss significant changes before investing time in implementation.
2. **Follow standards:** Match the existing code style and structure.
3. **Test thoroughly:** Ensure all tests pass and add new tests for new functionality.
4. **Document:** Update relevant documentation for any user-facing changes.

## Code Review Process

All pull requests require:
- At least one approval from a maintainer
- All CI checks to pass
- Human review of all content (even if AI-assisted)

Changes to `policy/`, `curated/`, `index/schema/`, and `.github/` require approval from @wanikua per CODEOWNERS.

## Branch Protection

The `main` branch is protected and requires:
- At least one approving review
- All status checks to pass
- Linear history (no merge commits from contributors)

The `github-actions[bot]` account is permitted to push directly to `index/**` and `state/**` for automated index updates.

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project (see [`LICENSE`](LICENSE)).

## Questions?

If you have questions about contributing, please open an issue with the "question" label or refer to the documentation in the `docs/` directory.

Thank you for helping make the Agent Skills Index better!
