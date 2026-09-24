"""
Tests for evaluation datasets (S2-8).

Validates:
- Files exist and parse as JSONL
- Minimum counts
- Required fields present
- Labels in allowed sets
- No duplicate IDs
"""

import json
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).parent.parent / "eval"
DEDUP_PAIRS_FILE = EVAL_DIR / "dedup-pairs.jsonl"
SECURITY_SAMPLES_FILE = EVAL_DIR / "security-samples.jsonl"

ALLOWED_DEDUP_LABELS = {"exact-duplicate", "near-duplicate", "not-duplicate"}
ALLOWED_SECURITY_STATUSES = {"pass", "review", "warn", "malicious"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}

MIN_DEDUP_PAIRS = 300
MIN_SECURITY_SAMPLES = 100


def load_jsonl(path: Path) -> list[dict]:
    """Load and parse a JSONL file."""
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                pytest.fail(f"{path.name} line {line_no}: Invalid JSON: {e}")
    return items


class TestDedupPairs:
    """Tests for dedup-pairs.jsonl."""

    def test_file_exists(self):
        """Dedup pairs file must exist."""
        assert DEDUP_PAIRS_FILE.exists(), f"{DEDUP_PAIRS_FILE} not found"

    def test_valid_jsonl(self):
        """File must parse as valid JSONL."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        assert len(pairs) > 0, "File is empty"

    def test_minimum_count(self):
        """Must have at least 300 pairs."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        assert len(pairs) >= MIN_DEDUP_PAIRS, (
            f"Expected at least {MIN_DEDUP_PAIRS} pairs, got {len(pairs)}"
        )

    def test_required_fields(self):
        """Each pair must have required fields."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        required_fields = {"pair_id", "skill_a", "skill_b", "label", "notes"}
        skill_fields = {"name", "description", "content"}

        for i, pair in enumerate(pairs, 1):
            missing = required_fields - pair.keys()
            assert not missing, f"Pair {i} missing fields: {missing}"

            # Check skill_a
            assert isinstance(pair["skill_a"], dict), f"Pair {i}: skill_a must be dict"
            missing_a = skill_fields - pair["skill_a"].keys()
            assert not missing_a, f"Pair {i}: skill_a missing: {missing_a}"

            # Check skill_b
            assert isinstance(pair["skill_b"], dict), f"Pair {i}: skill_b must be dict"
            missing_b = skill_fields - pair["skill_b"].keys()
            assert not missing_b, f"Pair {i}: skill_b missing: {missing_b}"

    def test_valid_labels(self):
        """Labels must be in allowed set."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        for i, pair in enumerate(pairs, 1):
            label = pair.get("label")
            assert label in ALLOWED_DEDUP_LABELS, (
                f"Pair {i}: invalid label '{label}', must be one of {ALLOWED_DEDUP_LABELS}"
            )

    def test_unique_pair_ids(self):
        """pair_id must be unique."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        ids = [p["pair_id"] for p in pairs]
        duplicates = [id for id in ids if ids.count(id) > 1]
        assert not duplicates, f"Duplicate pair_ids: {set(duplicates)}"

    def test_pair_ids_are_integers(self):
        """pair_id must be integers."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        for i, pair in enumerate(pairs, 1):
            pid = pair.get("pair_id")
            assert isinstance(pid, int), f"Pair {i}: pair_id must be integer, got {type(pid).__name__}"

    def test_label_distribution(self):
        """Check label distribution (informational)."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        counts = {}
        for pair in pairs:
            label = pair["label"]
            counts[label] = counts.get(label, 0) + 1

        print("\nDedup label distribution:")
        for label, count in sorted(counts.items()):
            print(f"  {label}: {count}")

        # Should have at least some of each type
        for label in ALLOWED_DEDUP_LABELS:
            assert counts.get(label, 0) > 0, f"No pairs with label '{label}'"


class TestSecuritySamples:
    """Tests for security-samples.jsonl."""

    def test_file_exists(self):
        """Security samples file must exist."""
        assert SECURITY_SAMPLES_FILE.exists(), f"{SECURITY_SAMPLES_FILE} not found"

    def test_valid_jsonl(self):
        """File must parse as valid JSONL."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        assert len(samples) > 0, "File is empty"

    def test_minimum_count(self):
        """Must have at least 100 samples."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        assert len(samples) >= MIN_SECURITY_SAMPLES, (
            f"Expected at least {MIN_SECURITY_SAMPLES} samples, got {len(samples)}"
        )

    def test_required_fields(self):
        """Each sample must have required fields."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        required_fields = {
            "sample_id",
            "description",
            "text",
            "risk_level",
            "ioc_patterns",
            "status",
            "notes",
        }

        for i, sample in enumerate(samples, 1):
            missing = required_fields - sample.keys()
            assert not missing, f"Sample {i} missing fields: {missing}"

    def test_valid_statuses(self):
        """Status must be in allowed set."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        for i, sample in enumerate(samples, 1):
            status = sample.get("status")
            assert status in ALLOWED_SECURITY_STATUSES, (
                f"Sample {i}: invalid status '{status}', must be one of {ALLOWED_SECURITY_STATUSES}"
            )

    def test_valid_risk_levels(self):
        """risk_level must be in allowed set."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        for i, sample in enumerate(samples, 1):
            risk = sample.get("risk_level")
            assert risk in ALLOWED_RISK_LEVELS, (
                f"Sample {i}: invalid risk_level '{risk}', must be one of {ALLOWED_RISK_LEVELS}"
            )

    def test_ioc_patterns_is_list(self):
        """ioc_patterns must be a list."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        for i, sample in enumerate(samples, 1):
            ioc = sample.get("ioc_patterns")
            assert isinstance(ioc, list), (
                f"Sample {i}: ioc_patterns must be list, got {type(ioc).__name__}"
            )

    def test_unique_sample_ids(self):
        """sample_id must be unique."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        ids = [s["sample_id"] for s in samples]
        duplicates = [id for id in ids if ids.count(id) > 1]
        assert not duplicates, f"Duplicate sample_ids: {set(duplicates)}"

    def test_sample_ids_are_integers(self):
        """sample_id must be integers."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        for i, sample in enumerate(samples, 1):
            sid = sample.get("sample_id")
            assert isinstance(sid, int), f"Sample {i}: sample_id must be integer, got {type(sid).__name__}"

    def test_no_executable_content(self):
        """Samples should not contain actual executable code (basic heuristic check)."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        suspicious_markers = [
            b'\x7fELF',  # ELF binary
            b'MZ\x90',   # DOS/PE binary
            b'\xcf\xfa\xed\xfe',  # Mach-O binary
        ]

        for i, sample in enumerate(samples, 1):
            text_bytes = sample["text"].encode("utf-8")
            for marker in suspicious_markers:
                assert marker not in text_bytes, (
                    f"Sample {i} contains binary signature {marker.hex()}"
                )

    def test_status_distribution(self):
        """Check status distribution (informational)."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        status_counts = {}
        risk_counts = {}

        for sample in samples:
            status = sample["status"]
            risk = sample["risk_level"]
            status_counts[status] = status_counts.get(status, 0) + 1
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

        print("\nSecurity status distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")

        print("\nRisk level distribution:")
        for risk, count in sorted(risk_counts.items()):
            print(f"  {risk}: {count}")

        # Should have examples of each status
        for status in ALLOWED_SECURITY_STATUSES:
            assert status_counts.get(status, 0) > 0, f"No samples with status '{status}'"

        # Should have examples of each risk level
        for risk in ALLOWED_RISK_LEVELS:
            assert risk_counts.get(risk, 0) > 0, f"No samples with risk_level '{risk}'"

    def test_malicious_samples_have_ioc_patterns(self):
        """Malicious samples should have IOC patterns."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        for i, sample in enumerate(samples, 1):
            if sample["status"] == "malicious":
                ioc_patterns = sample.get("ioc_patterns", [])
                # Most malicious samples should have IOC patterns
                # (but we allow exceptions for behavioral indicators)
                if not ioc_patterns:
                    print(f"Warning: Sample {i} is malicious but has no IOC patterns")

    def test_pass_samples_have_no_ioc_patterns(self):
        """Pass samples should have empty IOC patterns."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        for i, sample in enumerate(samples, 1):
            if sample["status"] == "pass":
                ioc_patterns = sample.get("ioc_patterns", [])
                assert not ioc_patterns, (
                    f"Sample {i} has status 'pass' but has IOC patterns: {ioc_patterns}"
                )


class TestCoverage:
    """Test that datasets cover required scenarios from PLAN.md."""

    def test_anthropics_exact_duplicates(self):
        """Must have anthropics docx/pdf/excel/pptx exact duplicates."""
        pairs = load_jsonl(DEDUP_PAIRS_FILE)
        exact_pairs = [p for p in pairs if p["label"] == "exact-duplicate"]

        # Check for office format skills
        office_formats = {"pdf", "docx", "excel", "pptx"}
        found_formats = set()

        for pair in exact_pairs:
            name_a = pair["skill_a"]["name"].lower()
            name_b = pair["skill_b"]["name"].lower()
            for fmt in office_formats:
                if fmt in name_a or fmt in name_b:
                    found_formats.add(fmt)

        print(f"\nFound exact-duplicate pairs for formats: {found_formats}")
        # At least some office format duplicates
        assert found_formats, "No office format exact duplicates found"

    def test_curl_pipe_sh_pattern(self):
        """Must have curl|sh IOC pattern samples."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        found = False
        for sample in samples:
            if any("curl|sh" in p or "curl.*sh" in p for p in sample["ioc_patterns"]):
                found = True
                break
        assert found, "No samples with curl|sh pattern"

    def test_base64_bash_pattern(self):
        """Must have base64|bash IOC pattern samples."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        found = False
        for sample in samples:
            if any("base64" in p and ("bash" in p or "sh" in p) for p in sample["ioc_patterns"]):
                found = True
                break
        assert found, "No samples with base64|bash pattern"

    def test_ssh_credential_access(self):
        """Must have SSH credential access samples."""
        samples = load_jsonl(SECURITY_SAMPLES_FILE)
        found = False
        for sample in samples:
            if any(".ssh" in p for p in sample["ioc_patterns"]):
                found = True
                break
        assert found, "No samples with .ssh pattern"
