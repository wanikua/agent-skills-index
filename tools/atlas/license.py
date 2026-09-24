"""License resolution for Agent Skills.

This module implements the per-skill license detection algorithm described in
docs/research/2026-09-24/seeds-licensing.md § 2 and PLAN.md § S1-5.
"""

import json
import re
from pathlib import Path
from typing import Any, Literal, TypedDict

from license_expression import get_spdx_licensing

# Load SPDX licensing instance
licensing = get_spdx_licensing()


class LicenseInfo(TypedDict):
    """License information for a skill."""

    declared: str | None
    spdx: str
    evidence: Literal[
        "frontmatter",
        "skill-file",
        "ancestor-file",
        "repo-file",
        "readme",
        "none",
    ]
    file: str | None
    class_: Literal["allow", "conditional", "deny", "unknown"]
    needs_review: bool
    conflict_info: dict[str, Any] | None


class LicenseClassifier:
    """Classifies licenses into allow/conditional/deny/unknown."""

    def __init__(self, policy_dir: Path | None = None):
        """Initialize classifier with policy files.

        Args:
            policy_dir: Path to policy directory. Defaults to workspace/policy/.
        """
        if policy_dir is None:
            policy_dir = Path(__file__).parents[2] / "policy"

        with open(policy_dir / "licenses.json") as f:
            policy = json.load(f)
            self.allow: set[str] = set(policy["allow"])
            self.conditional: set[str] = set(policy["conditional"])
            self.deny: set[str] = set(policy["deny"])

        with open(policy_dir / "license-aliases.json") as f:
            aliases_data = json.load(f)
            self.aliases: dict[str, str] = aliases_data["aliases"]
            self.url_patterns: dict[str, str] = aliases_data["url_patterns"]

    def normalize(self, license_str: str | None) -> str | None:
        """Normalize a license string.

        Args:
            license_str: Raw license string from frontmatter or file.

        Returns:
            Normalized SPDX identifier or original string if no match.
        """
        if not license_str:
            return None

        # Trim whitespace and quotes
        license_str = license_str.strip().strip('"\'')

        # Check if it's a URL
        for url, spdx in self.url_patterns.items():
            if url in license_str:
                return spdx

        # Remove trailing "license" or "License"
        normalized = re.sub(r"\s+[Ll]icense$", "", license_str)

        # Check aliases
        if normalized in self.aliases:
            return self.aliases[normalized]

        # Try original string in aliases
        if license_str in self.aliases:
            return self.aliases[license_str]

        return license_str

    def classify(self, spdx_expr: str) -> tuple[Literal["allow", "conditional", "deny", "unknown"], bool]:
        """Classify an SPDX expression.

        Args:
            spdx_expr: SPDX license expression.

        Returns:
            Tuple of (classification, needs_review).
        """
        if spdx_expr in ("NOASSERTION", "LicenseRef-Unrecognized"):
            return ("unknown", True)

        # LicenseRef-Proprietary is explicit deny, doesn't need review
        if spdx_expr == "LicenseRef-Proprietary":
            return ("deny", False)

        if spdx_expr.startswith("LicenseRef-"):
            return ("deny", True)

        # Parse SPDX expression to get individual licenses
        try:
            parsed = licensing.parse(spdx_expr, validate=True)
        except Exception:
            return ("unknown", True)

        # Get all license keys from the expression
        license_keys = set()
        for symbol in parsed.symbols:
            if hasattr(symbol, "key"):
                license_keys.add(symbol.key)

        if not license_keys:
            return ("unknown", True)

        # Determine strictest classification
        has_deny = any(lic in self.deny for lic in license_keys)
        has_conditional = any(lic in self.conditional for lic in license_keys)
        has_allow = any(lic in self.allow for lic in license_keys)
        has_unknown = any(lic not in (self.allow | self.conditional | self.deny) for lic in license_keys)

        # If any deny or unknown, that takes precedence
        if has_deny:
            return ("deny", has_conditional or has_allow)
        if has_unknown:
            return ("unknown", True)
        if has_conditional:
            return ("conditional", has_allow)
        if has_allow:
            return ("allow", False)

        return ("unknown", True)


class LicenseResolver:
    """Resolves license for a skill based on algorithm in seeds-licensing.md § 2."""

    # Common LICENSE file names (case-insensitive match)
    LICENSE_NAMES = [
        "LICENSE",
        "LICENCE",
        "COPYING",
        "LICENSE.txt",
        "LICENSE.md",
        "LICENSE.rst",
        "LICENCE.txt",
        "LICENCE.md",
        "COPYING.txt",
        "COPYING.md",
    ]

    # Simple text fingerprints for common licenses
    MIT_FINGERPRINTS = [
        "Permission is hereby granted, free of charge",
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY",
    ]

    APACHE_FINGERPRINTS = [
        "Apache License",
        "Version 2.0, January 2004",
        "http://www.apache.org/licenses/",
    ]

    BSD_FINGERPRINTS = [
        "Redistribution and use in source and binary forms",
        "THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS",
    ]

    ISC_FINGERPRINTS = [
        "Permission to use, copy, modify, and/or distribute",
        "ISC License",
    ]

    CC_BY_FINGERPRINTS = [
        "Creative Commons Attribution",
        "creativecommons.org/licenses/by/",
    ]

    CC_BY_SA_FINGERPRINTS = [
        "Creative Commons Attribution-ShareAlike",
        "creativecommons.org/licenses/by-sa/",
    ]

    def __init__(self, repo_root: Path, classifier: LicenseClassifier | None = None):
        """Initialize resolver.

        Args:
            repo_root: Root directory of the repository.
            classifier: License classifier instance. Creates new one if None.
        """
        self.repo_root = Path(repo_root)
        self.classifier = classifier or LicenseClassifier()

    def resolve_skill_license(
        self,
        skill_path: Path,
        frontmatter_license: str | None = None,
        readme_content: str | None = None,
    ) -> LicenseInfo:
        """Resolve license for a single skill.

        Args:
            skill_path: Path to SKILL.md file (absolute or relative to repo_root).
            frontmatter_license: License string from frontmatter.
            readme_content: Content of README.md if present (for license section extraction).

        Returns:
            LicenseInfo dictionary with resolved license information.
        """
        # Make skill_path relative to repo_root if it's absolute
        if skill_path.is_absolute():
            try:
                skill_path = skill_path.relative_to(self.repo_root)
            except ValueError:
                pass

        skill_dir = skill_path.parent

        # Step 1: Check frontmatter license
        if frontmatter_license:
            result = self._resolve_from_frontmatter(frontmatter_license, skill_dir)
            if result:
                return result

        # Step 2: Check skill directory for LICENSE files
        result = self._find_license_in_dir(skill_dir, evidence="skill-file")
        if result:
            return result

        # Step 3: Check ancestor directories
        result = self._find_license_in_ancestors(skill_dir)
        if result:
            return result

        # Step 4: Check root directory
        result = self._find_license_in_dir(Path("."), evidence="repo-file")
        if result:
            return result

        # Step 5: Try to extract from README
        if readme_content:
            result = self._extract_from_readme(readme_content)
            if result:
                return result

        # Step 6: No license found
        return self._make_license_info(
            declared=None,
            spdx="NOASSERTION",
            evidence="none",
            file=None,
            class_="unknown",
            needs_review=True,
        )

    def _resolve_from_frontmatter(self, license_str: str, skill_dir: Path) -> LicenseInfo | None:
        """Resolve license from frontmatter field.

        Args:
            license_str: Raw license string from frontmatter.
            skill_dir: Directory containing the skill.

        Returns:
            LicenseInfo if resolved, None to continue to next step.
        """
        # Check if it starts with "Proprietary"
        if license_str.strip().startswith("Proprietary"):
            return self._make_license_info(
                declared=license_str,
                spdx="LicenseRef-Proprietary",
                evidence="frontmatter",
                file=None,
                class_="deny",
                needs_review=False,
            )

        # Check if it's a file reference
        if self._is_file_reference(license_str):
            # Try to find and read the referenced file
            license_file = self._find_referenced_file(license_str, skill_dir)
            if license_file:
                return self._resolve_from_file(license_file, evidence="skill-file")
            else:
                # Dangling reference
                return self._make_license_info(
                    declared=license_str,
                    spdx="NOASSERTION",
                    evidence="frontmatter",
                    file=None,
                    class_="unknown",
                    needs_review=True,
                    conflict_info={"error": "dangling-license-ref"},
                )

        # Try to normalize and parse as SPDX
        normalized = self.classifier.normalize(license_str)
        if not normalized:
            return self._make_license_info(
                declared=license_str,
                spdx="LicenseRef-Unrecognized",
                evidence="frontmatter",
                file=None,
                class_="unknown",
                needs_review=True,
            )

        # Try parsing as SPDX expression
        try:
            licensing.parse(normalized, validate=True)
            spdx = normalized
        except Exception:
            # Not a valid SPDX expression
            return self._make_license_info(
                declared=license_str,
                spdx="LicenseRef-Unrecognized",
                evidence="frontmatter",
                file=None,
                class_="unknown",
                needs_review=True,
            )

        class_, needs_review = self.classifier.classify(spdx)
        return self._make_license_info(
            declared=license_str,
            spdx=spdx,
            evidence="frontmatter",
            file=None,
            class_=class_,
            needs_review=needs_review,
        )

    def _is_file_reference(self, license_str: str) -> bool:
        """Check if a license string is a file reference."""
        lower = license_str.lower()
        return (
            any(name.lower() in lower for name in self.LICENSE_NAMES)
            and any(word in lower for word in ["see", "in", "has", "complete terms"])
        ) or (license_str.strip().upper() in [n.upper() for n in self.LICENSE_NAMES])

    def _find_referenced_file(self, license_str: str, skill_dir: Path) -> Path | None:
        """Find a license file referenced in the license string."""
        # Extract potential filenames from the string
        for name in self.LICENSE_NAMES:
            if name.lower() in license_str.lower():
                # Try in skill directory
                candidate = self.repo_root / skill_dir / name
                if candidate.exists():
                    return candidate
                # Try variations
                for ext in [".txt", ".md", ".rst", ""]:
                    candidate = self.repo_root / skill_dir / (name + ext)
                    if candidate.exists():
                        return candidate

        return None

    def _find_license_in_dir(self, directory: Path, evidence: str) -> LicenseInfo | None:
        """Find and resolve license file in a specific directory."""
        dir_path = self.repo_root / directory

        if not dir_path.exists():
            return None

        # Look for LICENSE files (case-insensitive)
        for entry in dir_path.iterdir():
            if entry.is_file() and entry.name.upper() in [n.upper() for n in self.LICENSE_NAMES]:
                return self._resolve_from_file(entry, evidence=evidence)

        return None

    def _find_license_in_ancestors(self, skill_dir: Path) -> LicenseInfo | None:
        """Find license in ancestor directories between skill and root."""
        current = skill_dir.parent

        while current != Path("."):
            result = self._find_license_in_dir(current, evidence="ancestor-file")
            if result:
                return result
            current = current.parent

        return None

    def _resolve_from_file(self, license_file: Path, evidence: str) -> LicenseInfo | None:
        """Resolve license from a LICENSE file."""
        try:
            content = license_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        # Check if it's a pointer file (one line pointing to root)
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if len(lines) == 1 or (len(lines) <= 3 and any("see" in line.lower() for line in lines)):
            # Might be a pointer - try to resolve
            if "root" in content.lower() or ".." in content:
                return self._find_license_in_dir(Path("."), evidence="repo-file")

        # Try fingerprinting
        spdx = self._fingerprint_license(content)

        if not spdx:
            # Unknown/custom license - mark as vendor terms
            relative_path = license_file.relative_to(self.repo_root)
            # Extract vendor name from path
            parts = relative_path.parts
            vendor = parts[0] if parts else "unknown"
            spdx = f"LicenseRef-{vendor}-terms"

        class_, needs_review = self.classifier.classify(spdx)

        relative_path = str(license_file.relative_to(self.repo_root))
        return self._make_license_info(
            declared=None,
            spdx=spdx,
            evidence=evidence,
            file=relative_path,
            class_=class_,
            needs_review=needs_review,
        )

    def _fingerprint_license(self, content: str) -> str | None:
        """Fingerprint license text to identify common licenses.

        Args:
            content: License file content.

        Returns:
            SPDX identifier or None if not recognized.
        """
        content_lower = content.lower()

        # Check for MIT
        if all(fp.lower() in content_lower for fp in self.MIT_FINGERPRINTS):
            return "MIT"

        # Check for Apache-2.0
        if all(fp.lower() in content_lower for fp in self.APACHE_FINGERPRINTS):
            return "Apache-2.0"

        # Check for BSD
        if all(fp.lower() in content_lower for fp in self.BSD_FINGERPRINTS):
            # Try to distinguish between BSD-2-Clause and BSD-3-Clause
            if "neither the name" in content_lower or "3." in content:
                return "BSD-3-Clause"
            else:
                return "BSD-2-Clause"

        # Check for ISC
        if all(fp.lower() in content_lower for fp in self.ISC_FINGERPRINTS):
            return "ISC"

        # Check for CC-BY-SA first (more specific)
        if all(fp.lower() in content_lower for fp in self.CC_BY_SA_FINGERPRINTS):
            return "CC-BY-SA-4.0"

        # Check for CC-BY
        if all(fp.lower() in content_lower for fp in self.CC_BY_FINGERPRINTS):
            return "CC-BY-4.0"

        return None

    def _extract_from_readme(self, readme_content: str) -> LicenseInfo | None:
        """Extract license from README License section."""
        # Look for License section
        lines = readme_content.split("\n")
        in_license_section = False
        license_lines = []

        for line in lines:
            # Check for License heading
            if re.match(r"^#+\s*License\s*$", line, re.IGNORECASE):
                in_license_section = True
                continue

            if in_license_section:
                # Stop at next heading
                if line.startswith("#"):
                    break
                if line.strip():
                    license_lines.append(line.strip())

        if not license_lines:
            return None

        # Try to extract license name - join all lines and normalize
        license_text = " ".join(license_lines)

        # First try the whole text
        normalized = self.classifier.normalize(license_text.strip())

        # If that doesn't work, try just the first non-empty line
        if not normalized or normalized == license_text.strip():
            first_line = license_lines[0].strip() if license_lines else ""
            normalized = self.classifier.normalize(first_line)

        if normalized:
            # Try parsing as SPDX expression
            try:
                licensing.parse(normalized, validate=True)
                # README evidence is not sufficient for curation
                return self._make_license_info(
                    declared=license_text,
                    spdx=normalized,
                    evidence="readme",
                    file=None,
                    class_="unknown",
                    needs_review=True,
                )
            except Exception:
                pass

        return None

    def _make_license_info(
        self,
        declared: str | None,
        spdx: str,
        evidence: str,
        file: str | None,
        class_: str,
        needs_review: bool,
        conflict_info: dict | None = None,
    ) -> LicenseInfo:
        """Create a LicenseInfo dictionary."""
        return {
            "declared": declared,
            "spdx": spdx,
            "evidence": evidence,
            "file": file,
            "class_": class_,
            "needs_review": needs_review,
            "conflict_info": conflict_info,
        }


def resolve_license(
    repo_root: Path,
    skill_path: Path,
    frontmatter_license: str | None = None,
    readme_content: str | None = None,
) -> LicenseInfo:
    """Resolve license for a skill (convenience function).

    Args:
        repo_root: Root directory of the repository.
        skill_path: Path to SKILL.md file.
        frontmatter_license: License string from frontmatter.
        readme_content: README content for license extraction.

    Returns:
        LicenseInfo dictionary.
    """
    resolver = LicenseResolver(repo_root)
    return resolver.resolve_skill_license(skill_path, frontmatter_license, readme_content)
