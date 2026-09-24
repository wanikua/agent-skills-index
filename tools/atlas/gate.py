#!/usr/bin/env python3
"""Gate integration for skill index filtering.

Implements S2-7: gate checks for source and curated layers.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GateResult:
    """Result of a gate check."""

    passes: bool
    reasons: list[str] = field(default_factory=list)
    gate_type: str = ""  # "source" | "curated"
    skill_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON output."""
        return {
            "skill_id": self.skill_id,
            "gate": self.gate_type,
            "passes": self.passes,
            "reasons": self.reasons,
        }


# Blocking smells for curated layer (from PLAN §S2-6)
BLOCKING_SMELLS = {
    "description-too-long",  # > 1024 chars
    "description-too-short",  # < 40 chars
    "description-has-xml-tags",  # XML tags in description
    "reserved-word-name",  # Uses anthropic/claude as name
}


def gate_source(skill_record: dict[str, Any]) -> GateResult:
    """
    Check if a skill meets source layer gate requirements.

    Source gate is lighter: just check that the skill is:
    - Not malicious
    - Owner not dangling
    - Has required identity/hash fields

    Args:
        skill_record: Skill record from index

    Returns:
        GateResult with pass/fail and reasons
    """
    skill_id = skill_record.get("id", "unknown")
    reasons = []

    # Check status: must not be dangling
    status = skill_record.get("status")
    if status == "dangling":
        reasons.append("Skill status is 'dangling' (owner or repo no longer exists)")

    # Check security status: must not be malicious
    security = skill_record.get("security", {})
    sec_status = security.get("status")
    if sec_status == "malicious":
        reasons.append("Security status is 'malicious'")

    # Check required identity fields
    if not skill_record.get("id"):
        reasons.append("Missing required field: id")
    if not skill_record.get("name"):
        reasons.append("Missing required field: name")
    if not skill_record.get("description"):
        reasons.append("Missing required field: description")

    # Check required hash fields
    hashes = skill_record.get("hashes", {})
    if not hashes.get("skill_md_sha256"):
        reasons.append("Missing required hash: skill_md_sha256")
    if not hashes.get("content_hash"):
        reasons.append("Missing required hash: content_hash")
    if not hashes.get("folder_sha256"):
        reasons.append("Missing required hash: folder_sha256")

    # Check source metadata
    source = skill_record.get("source", {})
    if not source.get("commit"):
        reasons.append("Missing source commit SHA")

    passes = len(reasons) == 0
    return GateResult(passes=passes, reasons=reasons, gate_type="source", skill_id=skill_id)


def gate_curated(skill_record: dict[str, Any]) -> GateResult:
    """
    Check if a skill meets curated layer gate requirements.

    Curated gate combines:
    - S1-7 conditions (proper SKILL.md, license class, hashes, trust/tier, conformance)
    - S2-4 security (no unresolved HIGH/CRITICAL, not malicious)
    - S2-5 external refs (no dangling owner, no critical dangling refs)
    - S2-6 quality (no blocking smells)
    - Human approval (evidence in record)

    Args:
        skill_record: Skill record from index

    Returns:
        GateResult with pass/fail and reasons
    """
    skill_id = skill_record.get("id", "unknown")
    reasons = []

    # S1-7: Filename must be exactly SKILL.md (not lowercase)
    conformance = skill_record.get("conformance", {})
    errors = conformance.get("errors", [])
    if "filename-lowercase" in errors:
        reasons.append("SKILL.md filename must be exact case (not skill.md)")

    # S1-7: Must pass strict conformance
    if not conformance.get("strict"):
        reasons.append("Frontmatter does not pass strict conformance")
        # Add specific conformance errors
        for error in errors:
            if error not in ["filename-lowercase"]:  # Already covered above
                reasons.append(f"Conformance error: {error}")

    # S1-7: License must be in allow or conditional class
    license_info = skill_record.get("license", {})
    license_class = license_info.get("class")
    if license_class not in ["allow", "conditional"]:
        reasons.append(f"License class must be 'allow' or 'conditional', got '{license_class}'")

    # S1-7: For conditional licenses, must have NOTICE/ATTRIBUTION
    if license_class == "conditional":
        curated_path = skill_record.get("curated_path")
        if curated_path:
            # Check for NOTICE or ATTRIBUTION file
            repo_root = Path.cwd()
            curated_full_path = repo_root / curated_path
            has_notice = (curated_full_path / "NOTICE").exists()
            has_attribution = (curated_full_path / "ATTRIBUTION.md").exists()
            if not (has_notice or has_attribution):
                reasons.append("Conditional license requires NOTICE or ATTRIBUTION file")

    # S1-7: Must have LICENSE file in curated path
    curated_path = skill_record.get("curated_path")
    if curated_path:
        repo_root = Path.cwd()
        license_path = repo_root / curated_path / "LICENSE"
        if not license_path.exists():
            reasons.append("Missing LICENSE file in curated directory")
    else:
        reasons.append("Missing curated_path (skill not mirrored to curated/)")

    # S1-7: Trust tier requirements
    trust_tier = skill_record.get("trust_tier")
    if trust_tier == "aggregator-copy":
        reasons.append("Aggregator copies cannot be curated (must be from canonical source)")

    # S2-4 Security: Status must be pass (or review with human approval)
    security = skill_record.get("security", {})
    sec_status = security.get("status")
    if sec_status == "malicious":
        reasons.append("Security status is 'malicious'")
    elif sec_status == "error":
        reasons.append("Security scan failed with errors")

    # S2-4: No unresolved HIGH or CRITICAL findings
    for scan in security.get("scans", []):
        ioc_patterns = scan.get("ioc_patterns", [])
        for ioc in ioc_patterns:
            severity = ioc.get("severity", "").lower()
            if severity in ["high", "critical"]:
                reasons.append(f"Unresolved {severity.upper()} security finding: {ioc.get('name', 'unknown')}")

    # S2-4: Dual-engine scan requirement for curated (best-effort)
    # Per PLAN: "dual-engine hooks can remain best-effort stubs if external engines absent"
    # Allow single IOC scanner if external scanners are unavailable
    scans = security.get("scans", [])
    engine_names = [s.get("engine") for s in scans]
    has_ioc = "ioc_scanner" in engine_names
    has_external = any(e in ["skillspector", "cisco-skill-scanner"] for e in engine_names)

    if not has_ioc:
        reasons.append("Missing IOC scanner (required)")
    elif not has_external:
        # Log but don't fail - external scanners are best-effort
        logger.debug("External security scanners unavailable (best-effort, not blocking)")

    # S2-5: No dangling owner/repo
    status = skill_record.get("status")
    if status == "dangling":
        reasons.append("Skill status is 'dangling' (owner or source no longer exists)")

    # S2-5: Check for critical dangling external refs
    external_refs = security.get("external_refs", [])
    for ref in external_refs:
        if not ref.get("exists") and ref.get("critical", False):
            reasons.append(f"Critical external reference is dangling: {ref.get('reference', 'unknown')}")

    # S2-6: No blocking quality smells
    quality = skill_record.get("quality", {})
    smells = quality.get("smells", [])
    blocking = [s for s in smells if s in BLOCKING_SMELLS]
    if blocking:
        for smell in blocking:
            reasons.append(f"Blocking quality smell: {smell}")

    # Human approval check
    # Look for evidence of human approval:
    # - layer == "curated" means it passed the atlas curate flow
    # - curated_path is set
    # - Could also check for a specific approval field if added
    layer = skill_record.get("layer")
    if layer != "curated":
        reasons.append("Skill layer is not 'curated' (no human approval)")

    # Note: Human approval is implicit in the curate workflow.
    # If a more explicit approval field is added (e.g., curation.approved_by),
    # we would check it here.

    passes = len(reasons) == 0
    return GateResult(passes=passes, reasons=reasons, gate_type="curated", skill_id=skill_id)


def check_curated_regression(repo_root: Path | None = None) -> list[tuple[str, GateResult]]:
    """
    Scan all curated entries and check if they still pass the curated gate.

    Used for regression watching: if a curated skill no longer passes,
    it should be flagged for review.

    Args:
        repo_root: Repository root (defaults to cwd)

    Returns:
        List of (skill_id, gate_result) tuples for skills that no longer pass
    """
    if repo_root is None:
        repo_root = Path.cwd()

    index_file = repo_root / "index" / "skills.jsonl"
    if not index_file.exists():
        logger.error(f"Index file not found: {index_file}")
        return []

    failing_skills = []

    with open(index_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            skill = json.loads(line)

            # Only check curated skills
            if skill.get("layer") != "curated":
                continue

            # Skip already-removed or quarantined skills
            if skill.get("status") in ["removed", "quarantined"]:
                continue

            # Check gate
            result = gate_curated(skill)
            if not result.passes:
                failing_skills.append((skill.get("id", "unknown"), result))

    return failing_skills
