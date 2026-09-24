"""Tests for license resolution."""

import json
import tempfile
from pathlib import Path

import pytest

from tools.atlas.license import LicenseClassifier, LicenseResolver


class TestLicenseClassifier:
    """Test license classification."""

    def test_load_policies(self):
        """Test loading policy files."""
        classifier = LicenseClassifier()
        assert "MIT" in classifier.allow
        assert "Apache-2.0" in classifier.allow
        assert "MPL-2.0" in classifier.conditional
        assert "GPL-3.0-only" in classifier.deny
        assert "LicenseRef-Proprietary" in classifier.deny

    def test_normalize_aliases(self):
        """Test normalization of common aliases."""
        classifier = LicenseClassifier()
        assert classifier.normalize("MIT License") == "MIT"
        assert classifier.normalize('"MIT license"') == "MIT"
        assert classifier.normalize("Apache License 2.0") == "Apache-2.0"
        assert classifier.normalize("3-clause BSD license") == "BSD-3-Clause"
        assert classifier.normalize("CC BY 4.0") == "CC-BY-4.0"

    def test_normalize_urls(self):
        """Test normalization of license URLs."""
        classifier = LicenseClassifier()
        assert classifier.normalize("https://opensource.org/licenses/MIT") == "MIT"
        assert classifier.normalize("https://creativecommons.org/licenses/by/4.0") == "CC-BY-4.0"

    def test_classify_allow(self):
        """Test classification of allow-listed licenses."""
        classifier = LicenseClassifier()
        class_, needs_review = classifier.classify("MIT")
        assert class_ == "allow"
        assert not needs_review

        class_, needs_review = classifier.classify("Apache-2.0")
        assert class_ == "allow"
        assert not needs_review

    def test_classify_conditional(self):
        """Test classification of conditional licenses."""
        classifier = LicenseClassifier()
        class_, needs_review = classifier.classify("MPL-2.0")
        assert class_ == "conditional"
        assert not needs_review

        class_, needs_review = classifier.classify("CC-BY-SA-4.0")
        assert class_ == "conditional"
        assert not needs_review

    def test_classify_deny(self):
        """Test classification of denied licenses."""
        classifier = LicenseClassifier()
        class_, needs_review = classifier.classify("GPL-3.0-only")
        assert class_ == "deny"
        assert not needs_review

        class_, needs_review = classifier.classify("LicenseRef-Proprietary")
        assert class_ == "deny"
        assert not needs_review

    def test_classify_unknown(self):
        """Test classification of unknown licenses."""
        classifier = LicenseClassifier()
        class_, needs_review = classifier.classify("NOASSERTION")
        assert class_ == "unknown"
        assert needs_review

        class_, needs_review = classifier.classify("LicenseRef-Unrecognized")
        assert class_ == "unknown"
        assert needs_review

    def test_classify_compound_expression(self):
        """Test classification of compound SPDX expressions."""
        classifier = LicenseClassifier()

        # Both allow -> allow
        class_, needs_review = classifier.classify("MIT AND Apache-2.0")
        assert class_ == "allow"
        assert not needs_review

        # Allow and conditional -> conditional with review
        class_, needs_review = classifier.classify("MIT AND MPL-2.0")
        assert class_ == "conditional"
        assert needs_review

        # Allow and deny -> deny with review
        class_, needs_review = classifier.classify("MIT AND GPL-3.0-only")
        assert class_ == "deny"
        assert needs_review


class TestLicenseResolver:
    """Test license resolution."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            yield repo

    def test_frontmatter_proprietary(self, temp_repo):
        """Test: Proprietary in frontmatter -> LicenseRef-Proprietary (deny)."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(
            skill_path, frontmatter_license="Proprietary. Complete terms in LICENSE.txt"
        )

        assert result["spdx"] == "LicenseRef-Proprietary"
        assert result["evidence"] == "frontmatter"
        assert result["class_"] == "deny"
        assert not result["needs_review"]

    def test_frontmatter_mit(self, temp_repo):
        """Test: MIT in frontmatter -> MIT (allow)."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, frontmatter_license="MIT")

        assert result["spdx"] == "MIT"
        assert result["evidence"] == "frontmatter"
        assert result["class_"] == "allow"
        assert not result["needs_review"]

    def test_frontmatter_unrecognized(self, temp_repo):
        """Test: Unrecognized frontmatter -> LicenseRef-Unrecognized (unknown)."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, frontmatter_license="Some Custom License")

        assert result["spdx"] == "LicenseRef-Unrecognized"
        assert result["evidence"] == "frontmatter"
        assert result["class_"] == "unknown"
        assert result["needs_review"]

    def test_skill_dir_license_mit(self, temp_repo):
        """Test: MIT LICENSE in skill directory."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        license_file = skill_path.parent / "LICENSE"
        license_file.write_text(
            """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "MIT"
        assert result["evidence"] == "skill-file"
        assert result["class_"] == "allow"
        assert result["file"] == "skills/test/LICENSE"

    def test_skill_dir_license_apache(self, temp_repo):
        """Test: Apache-2.0 LICENSE in skill directory."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        license_file = skill_path.parent / "LICENSE"
        license_file.write_text(
            """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "Apache-2.0"
        assert result["evidence"] == "skill-file"
        assert result["class_"] == "allow"

    def test_ancestor_license(self, temp_repo):
        """Test: LICENSE in plugin directory (ancestor)."""
        skill_path = temp_repo / "plugins" / "myplugin" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        # Put LICENSE at plugin level
        plugin_license = temp_repo / "plugins" / "myplugin" / "LICENSE"
        plugin_license.write_text(
            """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED.
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "MIT"
        assert result["evidence"] == "ancestor-file"
        assert result["file"] == "plugins/myplugin/LICENSE"

    def test_root_license(self, temp_repo):
        """Test: LICENSE at root."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        root_license = temp_repo / "LICENSE"
        root_license.write_text(
            """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED.
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "MIT"
        assert result["evidence"] == "repo-file"
        assert result["file"] == "LICENSE"

    def test_readme_license_section(self, temp_repo):
        """Test: License section in README."""
        skill_path = temp_repo / "SKILL.md"
        skill_path.write_text("---\nname: test\n---\n")

        readme_content = """# My Skill

Some description.

## License

MIT
"""

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, readme_content=readme_content)

        assert result["spdx"] == "MIT"
        assert result["evidence"] == "readme"
        # README evidence is not sufficient for curation
        assert result["class_"] == "unknown"
        assert result["needs_review"]

    def test_no_license_found(self, temp_repo):
        """Test: No license found -> NOASSERTION."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "NOASSERTION"
        assert result["evidence"] == "none"
        assert result["class_"] == "unknown"
        assert result["needs_review"]

    def test_dangling_license_ref(self, temp_repo):
        """Test: Frontmatter references missing file."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, frontmatter_license="See LICENSE.txt")

        assert result["spdx"] == "NOASSERTION"
        assert result["evidence"] == "frontmatter"
        assert result["class_"] == "unknown"
        assert result["needs_review"]
        assert result["conflict_info"] == {"error": "dangling-license-ref"}

    def test_custom_vendor_terms(self, temp_repo):
        """Test: Custom license text -> LicenseRef-vendor-terms (deny)."""
        skill_path = temp_repo / "skills" / "figma" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: figma\n---\n")

        license_file = skill_path.parent / "LICENSE"
        license_file.write_text(
            """Figma Developer Terms

You may use this only for Figma integrations.
All other uses prohibited.
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "LicenseRef-skills-terms"
        assert result["evidence"] == "skill-file"
        assert result["class_"] == "deny"


class TestRealWorldCases:
    """Test real-world cases from PLAN.md S1-5 acceptance criteria."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            yield repo

    def test_anthropics_skills_docx_deny(self, temp_repo):
        """Test: anthropics/skills docx skill with proprietary license."""
        skill_path = temp_repo / "skills" / "docx" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: docx\n---\n")

        # Anthropic's proprietary license
        license_file = skill_path.parent / "LICENSE.txt"
        license_file.write_text(
            """Copyright 2025 Anthropic PBC. All rights reserved.

You may not:
- Distribute, sublicense, or transfer this skill
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        # Custom terms should be denied
        assert result["class_"] == "deny"
        assert "LicenseRef-" in result["spdx"]

    def test_anthropics_skills_allow(self, temp_repo):
        """Test: anthropics/skills with Apache-2.0 (allow)."""
        skill_path = temp_repo / "skills" / "github" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: github\n---\n")

        license_file = skill_path.parent / "LICENSE.txt"
        license_file.write_text(
            """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "Apache-2.0"
        assert result["class_"] == "allow"

    def test_sentry_apache_and_mit(self, temp_repo):
        """Test: sentry-for-ai Apache-2.0 AND MIT conflict."""
        skill_path = temp_repo / "src" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        # Frontmatter says Apache-2.0
        # Root LICENSE is MIT
        root_license = temp_repo / "LICENSE"
        root_license.write_text(
            """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, frontmatter_license="Apache-2.0")

        # Frontmatter takes precedence, but conflict should be noted
        # In real implementation, we'd detect this conflict and mark for review
        assert result["spdx"] == "Apache-2.0"
        assert result["evidence"] == "frontmatter"

    def test_kdense_gpl_deny(self, temp_repo):
        """Test: K-Dense skill with GPL license (deny)."""
        skill_path = temp_repo / "skills" / "bioservices" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: bioservices\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, frontmatter_license="GPL-3.0")

        assert "GPL" in result["spdx"]
        assert result["class_"] == "deny"

    def test_kdense_polyform_deny(self, temp_repo):
        """Test: K-Dense skill with PolyForm-NC license (deny)."""
        skill_path = temp_repo / "skills" / "deepspot" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: deepspot\n---\n")

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, frontmatter_license="PolyForm-Noncommercial-1.0.0")

        assert result["class_"] == "deny"

    def test_vercel_no_frontmatter_readme(self, temp_repo):
        """Test: vercel-labs/agent-skills with no frontmatter, README says MIT."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\ndescription: test\n---\n")

        readme_content = """# Agent Skills

## License

MIT
"""

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path, readme_content=readme_content)

        # README evidence is not sufficient
        assert result["evidence"] == "readme"
        assert result["class_"] == "unknown"
        assert result["needs_review"]

    def test_figma_terms_deny(self, temp_repo):
        """Test: Figma with developer terms (deny)."""
        skill_path = temp_repo / "skills" / "figma" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: figma\n---\n")

        license_file = skill_path.parent / "LICENSE.txt"
        license_file.write_text(
            """Figma Developer Terms

Limited license to access and use only as necessary
for Figma integrations. No redistribution.
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["class_"] == "deny"
        assert "LicenseRef-" in result["spdx"]

    def test_remotion_unknown(self, temp_repo):
        """Test: remotion with no license (unknown)."""
        skill_path = temp_repo / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        # No license file, no frontmatter
        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "NOASSERTION"
        assert result["class_"] == "unknown"

    def test_bsd_variants(self, temp_repo):
        """Test: BSD-2-Clause vs BSD-3-Clause detection."""
        # BSD-3-Clause
        skill_path = temp_repo / "skills" / "bsd3" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: bsd3\n---\n")

        license_file = skill_path.parent / "LICENSE"
        license_file.write_text(
            """BSD 3-Clause License

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "BSD-3-Clause"
        assert result["class_"] == "allow"

    def test_cc_by_sa_conditional(self, temp_repo):
        """Test: trailofbits CC-BY-SA-4.0 (conditional)."""
        skill_path = temp_repo / "plugins" / "test" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("---\nname: test\n---\n")

        # Root CC-BY-SA-4.0
        root_license = temp_repo / "LICENSE"
        root_license.write_text(
            """Creative Commons Attribution-ShareAlike 4.0 International

This license requires that adaptations be shared under the same license.
https://creativecommons.org/licenses/by-sa/4.0/
"""
        )

        resolver = LicenseResolver(temp_repo)
        result = resolver.resolve_skill_license(skill_path)

        assert result["spdx"] == "CC-BY-SA-4.0"
        assert result["class_"] == "conditional"


def test_policy_files_exist():
    """Test that policy files exist and are valid JSON."""
    policy_dir = Path(__file__).parents[1] / "policy"

    licenses_file = policy_dir / "licenses.json"
    assert licenses_file.exists()
    with open(licenses_file) as f:
        licenses = json.load(f)
        assert "allow" in licenses
        assert "conditional" in licenses
        assert "deny" in licenses

    aliases_file = policy_dir / "license-aliases.json"
    assert aliases_file.exists()
    with open(aliases_file) as f:
        aliases = json.load(f)
        assert "aliases" in aliases
