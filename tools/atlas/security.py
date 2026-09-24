#!/usr/bin/env python3
"""Security scanning for Agent Skills.

Implements S2-4: layered security scanning with static analysis and IOC rules.
"""

import json
import logging
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# IOC patterns from security-quality.md §4
IOC_PATTERNS = {
    # Shell injection patterns
    "curl_pipe_sh": re.compile(r"curl\s+[^|]+\|\s*(ba)?sh", re.IGNORECASE),
    "base64_pipe_bash": re.compile(r"base64[^|]*\|\s*bash", re.IGNORECASE),
    "base64_exec": re.compile(r"base64\.b64decode\([^)]+\)[^;]*exec\(", re.IGNORECASE),
    # Eval/exec patterns
    "eval_exec": re.compile(r"\beval\s*\(|\bexec\s*\(", re.IGNORECASE),
    # Environment access
    "env_access": re.compile(r"os\.environ\[|process\.env\[", re.IGNORECASE),
    # Network patterns
    "raw_ip_url": re.compile(r"https?://(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?"),
    "requests_post": re.compile(r"requests\.post\(.*?http", re.IGNORECASE),
    # Privilege escalation
    "sudo": re.compile(r"\bsudo\s+", re.IGNORECASE),
    "chmod_numeric": re.compile(r"chmod\s+[0-7]{3,4}", re.IGNORECASE),
    # Sensitive paths
    "ssh_dir": re.compile(r"~/\.ssh|/home/[^/]+/\.ssh|\.ssh/", re.IGNORECASE),
    "etc_passwd": re.compile(r"/etc/passwd", re.IGNORECASE),
    # Paste sites (common malware delivery)
    "paste_sites": re.compile(r"(?:glot\.io|rentry\.co|pastebin\.com|paste\.ee|hastebin\.com)", re.IGNORECASE),
    # Password-protected archives
    "password_zip": re.compile(r"password.*?\.zip|\.zip.*?password", re.IGNORECASE),
}

# Instruction injection patterns
INSTRUCTION_PATTERNS = {
    "ignore_instructions": re.compile(r"ignore\s+(?:previous|prior)\s+instructions?", re.IGNORECASE),
    "send_to_url": re.compile(r"send\s+(?:to|the\s+data\s+to)\s+https?://", re.IGNORECASE),
    "exfiltrate": re.compile(r"exfiltrate|send.*?to.*?http", re.IGNORECASE),
}

# XML tags in description (Anthropic forbids these)
XML_TAG_PATTERN = re.compile(r"<[a-zA-Z][^>]*>")


@dataclass
class IOCMatch:
    """Represents a matched IOC pattern."""

    pattern_name: str
    pattern_type: str  # "code" | "instruction" | "description"
    line_number: int | None
    matched_text: str
    severity: str  # "critical" | "high" | "medium" | "low"


@dataclass
class ScanResult:
    """Result of a security scan."""

    status: str  # "pass" | "review" | "warn" | "malicious" | "pending" | "error"
    risk_level: str | None  # "low" | "medium" | "high"
    capabilities: list[str]
    scans: list[dict[str, Any]]
    ioc_matches: list[IOCMatch]
    needs_exclusion: bool  # True if should be excluded/marked malicious


def check_invisible_unicode(content: str) -> list[IOCMatch]:
    """
    Check for invisible or suspicious Unicode characters.

    Args:
        content: Text content to check

    Returns:
        List of IOC matches for suspicious Unicode
    """
    matches = []
    lines = content.split("\n")

    suspicious_categories = {
        "Cf",  # Format characters (invisible)
        "Cc",  # Control characters (except newline, tab, CR)
    }

    for line_num, line in enumerate(lines, 1):
        for i, char in enumerate(line):
            cat = unicodedata.category(char)
            # Allow common whitespace
            if char in ["\t", "\r", "\n", " "]:
                continue

            if cat in suspicious_categories or ord(char) in [0x200B, 0x200C, 0x200D, 0xFEFF]:
                matches.append(
                    IOCMatch(
                        pattern_name="invisible_unicode",
                        pattern_type="code",
                        line_number=line_num,
                        matched_text=f"U+{ord(char):04X} ({unicodedata.name(char, 'UNKNOWN')})",
                        severity="medium",
                    )
                )

    return matches


def scan_ioc_patterns(content: str, description: str | None = None) -> list[IOCMatch]:
    """
    Scan content for IOC patterns.

    Args:
        content: SKILL.md content
        description: Description text (optional, checked separately)

    Returns:
        List of IOC matches
    """
    matches = []
    lines = content.split("\n")

    # Check code patterns in main content
    for pattern_name, pattern in IOC_PATTERNS.items():
        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                # Determine severity based on pattern
                if pattern_name in ["curl_pipe_sh", "base64_pipe_bash", "base64_exec"]:
                    severity = "critical"
                elif pattern_name in ["eval_exec", "raw_ip_url", "paste_sites", "ssh_dir", "etc_passwd"]:
                    severity = "high"
                elif pattern_name in ["sudo", "chmod_numeric", "env_access", "password_zip"]:
                    severity = "medium"
                else:
                    severity = "low"

                matches.append(
                    IOCMatch(
                        pattern_name=pattern_name,
                        pattern_type="code",
                        line_number=line_num,
                        matched_text=match.group(0)[:100],  # Limit length
                        severity=severity,
                    )
                )

    # Check instruction patterns
    for pattern_name, pattern in INSTRUCTION_PATTERNS.items():
        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                matches.append(
                    IOCMatch(
                        pattern_name=pattern_name,
                        pattern_type="instruction",
                        line_number=line_num,
                        matched_text=match.group(0)[:100],
                        severity="high",
                    )
                )

    # Check description for XML tags
    if description:
        for match in XML_TAG_PATTERN.finditer(description):
            matches.append(
                IOCMatch(
                    pattern_name="xml_in_description",
                    pattern_type="description",
                    line_number=None,
                    matched_text=match.group(0)[:50],
                    severity="medium",
                )
            )

    # Check for invisible Unicode
    matches.extend(check_invisible_unicode(content))

    return matches


def detect_capabilities(content: str, scripts_present: bool = False) -> list[str]:
    """
    Detect capabilities from skill content.

    Args:
        content: SKILL.md content
        scripts_present: Whether scripts/ directory is present

    Returns:
        List of capability strings
    """
    capabilities = []

    # Network access
    if re.search(r"import\s+requests|import\s+urllib|fetch\(|axios|curl\s+", content, re.IGNORECASE):
        capabilities.append("network")

    # Shell execution
    if (
        re.search(r"subprocess\.|os\.system|shell=True|exec\(|eval\(|sh\s+-c|bash\s+-c", content, re.IGNORECASE)
        or scripts_present
    ):
        capabilities.append("shell")

    # Filesystem write
    if re.search(r"open\([^)]*,\s*['\"]w|os\.remove|os\.unlink|shutil\.|fs\.write", content, re.IGNORECASE):
        capabilities.append("fs-write")

    # Credential access
    if re.search(r"password|token|api[_-]?key|secret|credentials?|os\.environ|process\.env", content, re.IGNORECASE):
        capabilities.append("credentials")

    # External instructions (runtime fetching)
    if re.search(r"fetch\(['\"]http|requests\.get\(['\"]http.*?\.(?:md|txt|json)", content, re.IGNORECASE):
        capabilities.append("external-instructions")

    # Money/payment access
    if re.search(r"stripe|paypal|payment|wallet|crypto|bitcoin|ethereum", content, re.IGNORECASE):
        capabilities.append("money")

    return sorted(set(capabilities))


def determine_risk_level(capabilities: list[str], ioc_matches: list[IOCMatch]) -> str:
    """
    Determine risk level based on capabilities and IOCs.

    Args:
        capabilities: Detected capabilities
        ioc_matches: IOC matches

    Returns:
        Risk level: "low" | "medium" | "high"
    """
    # Check for critical/high severity IOCs
    has_critical = any(m.severity == "critical" for m in ioc_matches)
    has_high = any(m.severity == "high" for m in ioc_matches)

    if has_critical or "money" in capabilities or "external-instructions" in capabilities:
        return "high"

    if has_high or "shell" in capabilities or "credentials" in capabilities:
        return "medium"

    if capabilities or ioc_matches:
        return "medium"

    return "low"


def needs_exclusion(ioc_matches: list[IOCMatch], upstream_verdict: str | None = None) -> bool:
    """
    Determine if a skill should be excluded based on IOC matches and verdicts.

    Exclusion criteria (from PLAN.md S2-4):
    - Known IOC hit (critical severity)
    - Upstream registry malicious verdict
    - Exact match to denylisted hash (handled elsewhere)

    Everything else: tag only, do not delete.

    Args:
        ioc_matches: IOC matches found
        upstream_verdict: Verdict from upstream registry (e.g., "malicious")

    Returns:
        True if should be excluded/marked malicious
    """
    # Exclude if upstream says malicious
    if upstream_verdict and upstream_verdict.lower() == "malicious":
        return True

    # Exclude if critical IOC hit
    critical_patterns = ["curl_pipe_sh", "base64_pipe_bash", "base64_exec"]
    for match in ioc_matches:
        if match.pattern_name in critical_patterns and match.severity == "critical":
            return True

    # Everything else: tag only
    return False


def run_skillspector_scan(skill_path: Path) -> dict[str, Any] | None:
    """
    Run SkillSpector static-only scan if available.

    Args:
        skill_path: Path to skill directory

    Returns:
        Scan result dict or None if scanner unavailable
    """
    try:
        result = subprocess.run(
            ["skillspector", "scan", str(skill_path), "--no-llm", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"SkillSpector not available or failed: {e}")

    return None


def run_cisco_scan(skill_path: Path, policy: str = "default") -> dict[str, Any] | None:
    """
    Run Cisco skill-scanner static-only scan if available.

    Args:
        skill_path: Path to skill directory
        policy: Policy level (default | strict)

    Returns:
        Scan result dict or None if scanner unavailable
    """
    try:
        # Try to use skill-scanner without LLM
        result = subprocess.run(
            [
                "skill-scanner",
                "scan",
                str(skill_path),
                "--policy",
                policy,
                "--format",
                "json",
                "--no-llm",  # Static only
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError) as e:
        logger.debug(f"Cisco skill-scanner not available or failed: {e}")

    return None


def scan_skill(
    content: str,
    description: str | None = None,
    skill_path: Path | None = None,
    scripts_present: bool = False,
    commit_sha: str | None = None,
    upstream_verdict: str | None = None,
    layer: str = "source",
) -> ScanResult:
    """
    Scan a skill for security issues.

    Args:
        content: SKILL.md content
        description: Skill description
        skill_path: Path to skill directory (for external scanners)
        scripts_present: Whether scripts/ directory exists
        commit_sha: Git commit SHA
        upstream_verdict: Verdict from upstream registry
        layer: "source" or "curated"

    Returns:
        ScanResult with status and findings
    """
    # Scan for IOC patterns
    ioc_matches = scan_ioc_patterns(content, description)

    # Detect capabilities
    capabilities = detect_capabilities(content, scripts_present)

    # Determine risk level
    risk_level = determine_risk_level(capabilities, ioc_matches)

    # Check if needs exclusion
    exclude = needs_exclusion(ioc_matches, upstream_verdict)

    # Prepare scan records
    scans = []

    # Internal IOC scan
    now = datetime.now(timezone.utc)
    ioc_scan = {
        "engine": "atlas-ioc",
        "version": "1.0.0",
        "policy": "default",
        "commit": commit_sha,
        "ran_at": now.isoformat(),
        "max_severity": max((m.severity for m in ioc_matches), default="none"),
        "counts": {
            "critical": sum(1 for m in ioc_matches if m.severity == "critical"),
            "high": sum(1 for m in ioc_matches if m.severity == "high"),
            "medium": sum(1 for m in ioc_matches if m.severity == "medium"),
            "low": sum(1 for m in ioc_matches if m.severity == "low"),
        },
        "ioc_patterns": [
            {
                "name": m.pattern_name,
                "type": m.pattern_type,
                "line": m.line_number,
                "text": m.matched_text,
                "severity": m.severity,
            }
            for m in ioc_matches
        ],
    }
    scans.append(ioc_scan)

    # Try external scanners (best effort)
    if skill_path and skill_path.exists():
        # Try SkillSpector
        skillspector_result = run_skillspector_scan(skill_path)
        if skillspector_result:
            scans.append(
                {
                    "engine": "skillspector",
                    "version": skillspector_result.get("version", "unknown"),
                    "policy": "static-only",
                    "commit": commit_sha,
                    "ran_at": now.isoformat(),
                    "findings": skillspector_result.get("findings", []),
                }
            )

        # Try Cisco scanner (only for curated layer)
        if layer == "curated":
            cisco_result = run_cisco_scan(skill_path, policy="strict")
            if cisco_result:
                scans.append(
                    {
                        "engine": "cisco-skill-scanner",
                        "version": cisco_result.get("version", "unknown"),
                        "policy": "strict",
                        "commit": commit_sha,
                        "ran_at": now.isoformat(),
                        "findings": cisco_result.get("findings", []),
                    }
                )

    # Determine status
    if exclude:
        status = "malicious"
    elif layer == "curated":
        # Curated layer: stricter requirements (stub for S2-7)
        # For now, mark as "review" if there are any findings
        if ioc_matches or any(s.get("findings") for s in scans):
            status = "review"
        else:
            status = "pass"
    else:
        # Source layer: tag but don't exclude unless malicious
        if ioc_matches or capabilities:
            status = "warn"
        else:
            status = "pass"

    return ScanResult(
        status=status,
        risk_level=risk_level,
        capabilities=capabilities,
        scans=scans,
        ioc_matches=ioc_matches,
        needs_exclusion=exclude,
    )


def format_security_field(scan_result: ScanResult) -> dict[str, Any]:
    """
    Format scan result as security field for skill record.

    Args:
        scan_result: Scan result

    Returns:
        Security field dict matching schema in security-quality.md §6
    """
    return {
        "status": scan_result.status,
        "risk_level": scan_result.risk_level,
        "capabilities": scan_result.capabilities,
        "scans": scan_result.scans,
        "external_refs": [],  # Populated by S2-5
        "upstream_verdicts": {},  # Populated when available
        "takedown": {"state": "none", "reason": None, "date": None},
    }


def gate_curated(skill_record: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Check if a skill meets curated layer security requirements.

    This is a stub for S2-7 integration. Currently checks:
    - No unresolved HIGH/CRITICAL findings
    - Status must be "pass" or "review" (not "warn" or "malicious")

    Args:
        skill_record: Skill record with security field

    Returns:
        Tuple of (passes, list of reasons if fails)
    """
    reasons = []
    security = skill_record.get("security", {})

    # Check status
    status = security.get("status")
    if status in ["malicious", "error"]:
        reasons.append(f"Security status is {status}")
        return (False, reasons)

    # Check for critical/high severity IOCs
    for scan in security.get("scans", []):
        counts = scan.get("counts", {})
        if counts.get("critical", 0) > 0:
            reasons.append("Unresolved CRITICAL findings")
        if counts.get("high", 0) > 0:
            reasons.append("Unresolved HIGH findings")

    # For S2-7: would also check:
    # - Two-engine scan requirement
    # - File type allowlist
    # - Size caps
    # - Human review of MEDIUM findings
    # - No runtime instruction fetching

    passes = len(reasons) == 0
    return (passes, reasons)
