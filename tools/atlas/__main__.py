#!/usr/bin/env python3
"""Atlas CLI - Skill Atlas management tool."""

import argparse
import sys
from pathlib import Path


def cmd_validate(args):
    """Validate the index data and schema."""
    from tools.atlas.schema import validate_index
    from tools.atlas.stats import validate_readme_stats

    exit_code = 0

    # Schema validation
    if not args.wording:
        print("Validating index files against schemas...")
        all_valid, errors_by_file = validate_index()

        if all_valid:
            print("✓ All index files are valid")
        else:
            print("✗ Validation errors found:", file=sys.stderr)
            for filename, errors in errors_by_file.items():
                print(f"\n{filename}:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
            exit_code = 1

        # README stats validation
        print("Validating README stats block...")
        repo_root = Path.cwd()
        readme_path = repo_root / "README.md"
        stats_file = repo_root / "index" / "stats.json"

        is_valid, errors = validate_readme_stats(readme_path, stats_file)
        if is_valid:
            print("✓ README stats block is consistent with stats.json")
        else:
            print("✗ README stats validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            print("\nRun 'atlas stats --readme' to update the README", file=sys.stderr)
            exit_code = 1

    # Wording lint
    if args.wording:
        wording_lint_path = Path(__file__).parent.parent.parent / "tools" / "wording_lint.py"
        if wording_lint_path.exists():
            import subprocess

            result = subprocess.run([sys.executable, str(wording_lint_path)], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Wording lint failed:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
                return 1
            print("✓ Wording lint passed")
        else:
            print("Wording lint not available (tools/wording_lint.py not found), skipping")

    return exit_code


def cmd_crawl(args):
    """Crawl agent skills from sources."""
    import json
    import logging
    from pathlib import Path

    from tools.atlas import crawl

    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Determine workspace root
    repo_root = Path(__file__).parent.parent.parent

    # Load sources
    sources_file = repo_root / "index" / "sources.json"
    if not sources_file.exists():
        print(f"Error: {sources_file} not found", file=sys.stderr)
        return 1

    with open(sources_file) as f:
        sources_data = json.load(f)

    sources = sources_data.get("repositories", [])

    if not sources:
        print("No sources found in sources.json", file=sys.stderr)
        return 1

    # Set up directories
    state_dir = repo_root / "state" / "crawl"
    output_dir = repo_root / "build" / "raw"

    # Determine which sources to crawl
    if args.source:
        source_filter = args.source
    elif args.all:
        source_filter = None
    else:
        print("Error: Must specify either --source ID or --all", file=sys.stderr)
        return 1

    # Crawl
    result = crawl.crawl_sources(
        sources=sources,
        repo_root=repo_root,
        state_dir=state_dir,
        output_dir=output_dir,
        force=args.force,
        source_id_filter=source_filter,
    )

    if not result.get("success"):
        print(f"Crawl failed: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    # Print summary
    print("\nCrawl complete:")
    print(f"  Sources crawled: {result['sources_crawled']}")
    print(f"  Sources skipped (unchanged): {result['sources_skipped']}")
    print(f"  Sources failed: {result['sources_failed']}")
    print(f"  Total skills found: {result['total_skills']}")

    return 0


def cmd_build(args):
    """Build the index files from crawled data."""
    from pathlib import Path

    from tools.atlas import build

    repo_root = Path.cwd()
    raw_dir = repo_root / "build" / "raw"
    sources_file = repo_root / "index" / "sources.json"
    index_dir = repo_root / "index"

    if not sources_file.exists():
        print(f"Error: sources.json not found at {sources_file}", file=sys.stderr)
        return 1

    if not raw_dir.exists() or not list(raw_dir.glob("*.jsonl")):
        print(f"Warning: No crawl data found in {raw_dir}")
        print("Run 'atlas crawl --all' first to crawl skills.")
        return 1

    try:
        check_refs = getattr(args, "check_refs", False)
        if check_refs:
            print("External reference checking enabled (S2-5)")

        result = build.build_index(raw_dir, sources_file, index_dir, repo_root, check_external_refs=check_refs)
        print(f"✓ Built {result['skills_built']} skills from {result['sources_used']} sources")
        print(f"  - Total skills: {result['stats']['total_skills']}")
        print(f"  - Curated: {result['stats']['curated_skills']}")
        print(f"  - Repositories: {result['stats']['repositories']}")
        return 0
    except Exception as e:
        print(f"Build failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


def cmd_stats(args):
    """Generate statistics from the index."""
    from pathlib import Path

    from tools.atlas.stats import update_readme_stats

    repo_root = Path.cwd()
    readme_path = repo_root / "README.md"
    stats_file = repo_root / "index" / "stats.json"

    if not args.readme:
        print("Error: Currently only --readme is supported", file=sys.stderr)
        print("Usage: atlas stats --readme", file=sys.stderr)
        return 1

    try:
        updated = update_readme_stats(readme_path, stats_file)
        if updated:
            print("✓ README.md stats block updated")
        else:
            print("✓ README.md stats block already up to date")
        return 0
    except ValueError as e:
        print(f"✗ Failed to update README: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


def cmd_lint_skill(args):
    """Lint a skill directory for frontmatter conformance."""
    from pathlib import Path

    from tools.atlas.frontmatter import lint_skill

    skill_dir = Path(args.directory).resolve()

    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        return 1

    result = lint_skill(skill_dir, lenient=args.lenient)

    # Print results
    print(f"Skill directory: {skill_dir}")
    print(f"Strict mode: {'✓ PASS' if result.strict_valid else '✗ FAIL'}")
    print(f"Lenient mode: {'✓ PASS' if result.lenient_valid else '✗ FAIL'}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.dialects:
        print(f"\nInferred dialects: {', '.join(result.dialects)}")

    if result.extensions:
        print(f"\nExtensions: {', '.join(sorted(result.extensions.keys()))}")

    # Return exit code based on lenient mode result
    return 0 if result.lenient_valid else 1


def cmd_lint_quality(args):
    """Lint a skill directory for quality issues."""
    from pathlib import Path

    from tools.atlas.frontmatter import parse_content
    from tools.atlas.quality import lint_quality

    skill_dir = Path(args.directory).resolve()

    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        return 1

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {skill_dir}", file=sys.stderr)
        return 1

    # Read content and parse frontmatter to get name and description
    content = skill_md.read_text(encoding="utf-8")
    fm_result = parse_content(content, skill_dir.name)

    name = fm_result.get("frontmatter", {}).get("name")
    description = fm_result.get("frontmatter", {}).get("description")

    # Run quality linting
    result = lint_quality(skill_md_path=skill_md, name=name, description=description)

    # Print results
    print(f"Skill directory: {skill_dir}")
    print(f"Quality check: {'✓ PASS' if len(result.smells) == 0 else '✗ FAIL'}")

    if result.smells:
        print(f"\nQuality smells detected ({len(result.smells)}):")
        for smell in result.smells:
            print(f"  - {smell}")
    else:
        print("\nNo quality issues detected.")

    # Return 0 for pass, 1 for smells detected
    return 0 if len(result.smells) == 0 else 1


def cmd_sources_import(args):
    """Import sources from a JSON file."""
    from tools.atlas.sources import import_sources

    try:
        count = import_sources(args.file)
        print(f"✓ Successfully imported {count} sources")
        return 0
    except Exception as e:
        print(f"✗ Import failed: {e}", file=sys.stderr)
        return 1


def cmd_scan_security(args):
    """Scan a skill for security issues."""
    from pathlib import Path

    from tools.atlas import security

    skill_path = Path(args.directory).resolve()

    if not skill_path.is_dir():
        print(f"Error: {skill_path} is not a directory", file=sys.stderr)
        return 1

    # Find SKILL.md
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {skill_path}", file=sys.stderr)
        return 1

    # Read content
    try:
        with open(skill_md, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading SKILL.md: {e}", file=sys.stderr)
        return 1

    # Parse description from frontmatter if possible
    description = None
    try:
        from tools.atlas import frontmatter

        fm_result = frontmatter.parse_content(content, skill_path.name)
        description = fm_result.get("frontmatter", {}).get("description")
    except Exception:
        pass

    # Check for scripts/ directory
    scripts_present = (skill_path / "scripts").exists()

    # Run scan
    print(f"Scanning: {skill_path}")
    print(f"Scripts present: {scripts_present}")
    print()

    scan_result = security.scan_skill(
        content=content,
        description=description,
        skill_path=skill_path,
        scripts_present=scripts_present,
        layer=args.layer,
    )

    # Print results
    print(f"Status: {scan_result.status}")
    print(f"Risk Level: {scan_result.risk_level}")
    print(f"Capabilities: {', '.join(scan_result.capabilities) if scan_result.capabilities else 'none'}")
    print(f"Needs Exclusion: {scan_result.needs_exclusion}")
    print()

    if scan_result.ioc_matches:
        print(f"IOC Matches ({len(scan_result.ioc_matches)}):")
        for match in scan_result.ioc_matches:
            line_info = f" (line {match.line_number})" if match.line_number else ""
            print(f"  [{match.severity.upper()}] {match.pattern_name}{line_info}")
            print(f"    {match.matched_text}")
        print()

    print(f"Scans run: {len(scan_result.scans)}")
    for scan in scan_result.scans:
        engine = scan.get("engine", "unknown")
        counts = scan.get("counts", {})
        if counts:
            print(f"  {engine}: {counts}")

    if args.json:
        import json

        output = security.format_security_field(scan_result)
        print("\nJSON output:")
        print(json.dumps(output, indent=2, ensure_ascii=False))

    # Exit code based on status
    if scan_result.status in ["malicious", "error"]:
        return 1
    return 0


def cmd_gate(args):
    """Check if a skill meets gate requirements."""
    import json
    from pathlib import Path

    from tools.atlas import gate

    # Load skill record
    skill_id = args.skill_id
    index_file = Path.cwd() / "index" / "skills.jsonl"

    if not index_file.exists():
        print(f"Error: {index_file} not found", file=sys.stderr)
        return 1

    # Find skill
    skill = None
    with open(index_file, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record.get("id") == skill_id:
                skill = record
                break

    if not skill:
        print(f"Error: Skill {skill_id} not found in index", file=sys.stderr)
        return 1

    # Check gate
    if args.gate == "source":
        result = gate.gate_source(skill)
    elif args.gate == "curated":
        result = gate.gate_curated(skill)
    else:
        print(f"Error: Unknown gate type '{args.gate}'", file=sys.stderr)
        return 1

    # Output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Skill: {skill_id}")
        print(f"Gate: {args.gate}")
        print(f"Result: {'✓ PASS' if result.passes else '✗ FAIL'}")

        if result.reasons:
            print("\nReasons:")
            for reason in result.reasons:
                print(f"  - {reason}")

    return 0 if result.passes else 1


def cmd_check_curated_gate(args):
    """Check if curated skills still pass the gate (regression watcher)."""
    import json
    import os
    import subprocess
    from pathlib import Path

    from tools.atlas import gate

    repo_root = Path.cwd()

    # Check for failing skills
    print("Scanning curated skills for gate regressions...")
    failing = gate.check_curated_regression(repo_root)

    if not failing:
        print("✓ All curated skills pass the gate")
        return 0

    print(f"\n✗ Found {len(failing)} curated skills that no longer pass the gate:\n")

    for skill_id, result in failing:
        print(f"  {skill_id}")
        for reason in result.reasons:
            print(f"    - {reason}")
        print()

    # Update status to 'review' in index (unless --dry-run)
    if args.dry_run:
        print("--dry-run mode: not updating index or creating issues")
        return 1

    # Update index
    index_file = repo_root / "index" / "skills.jsonl"
    updated_skills = []
    skill_ids_to_update = {skill_id for skill_id, _ in failing}

    with open(index_file, encoding="utf-8") as f:
        for line in f:
            skill = json.loads(line)
            if skill.get("id") in skill_ids_to_update:
                # Mark as review
                if skill.get("status") != "review":
                    skill["status"] = "review"
                    print(f"Marked {skill['id']} as 'review'")
            updated_skills.append(skill)

    # Write back
    with open(index_file, "w", encoding="utf-8") as f:
        for skill in updated_skills:
            f.write(json.dumps(skill, ensure_ascii=False) + "\n")

    # Create GitHub issues (if GITHUB_TOKEN or GH_TOKEN available)
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not gh_token:
        print("\nNo GITHUB_TOKEN/GH_TOKEN found, skipping issue creation")
        print("(Issues would be created in CI with proper credentials)")
        return 1

    # Check if gh CLI is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\ngh CLI not available, skipping issue creation")
        return 1

    # Create issues
    print("\nCreating GitHub issues for failing skills...")
    for skill_id, result in failing:
        title = f"[Gate Regression] {skill_id} no longer passes curated gate"
        body = f"""## Skill Gate Regression

**Skill ID:** `{skill_id}`
**Gate:** curated

This skill was previously in the curated layer but no longer passes the curated gate.

### Reasons:

"""
        for reason in result.reasons:
            body += f"- {reason}\n"

        body += """

### Action Required

Please review this skill and either:
1. Fix the issues that caused the gate failure
2. Remove the skill from the curated layer
3. Update the gate requirements if they are too strict

**DO NOT** auto-delete this skill. Human review is required.
"""

        # Create issue
        try:
            result_proc = subprocess.run(
                ["gh", "issue", "create", "--title", title, "--body", body, "--label", "gate-regression"],
                capture_output=True,
                text=True,
                check=True,
            )
            issue_url = result_proc.stdout.strip()
            print(f"  Created issue for {skill_id}: {issue_url}")
        except subprocess.CalledProcessError as e:
            print(f"  Failed to create issue for {skill_id}: {e.stderr}")

    return 1


def cmd_discover(args):
    """Discover skill repositories from aggregator READMEs."""
    from tools.atlas.discover import run_discover

    output_path = Path(args.output) if args.output else Path("build/candidates.jsonl")
    return run_discover(output_path)


def cmd_dedup(args):
    """Run deduplication analysis on the index."""
    import json
    from pathlib import Path

    from tools.atlas.dedup import apply_deduplication, cluster_by_content_hash, compute_canonical_count

    repo_root = Path.cwd()
    index_file = repo_root / "index" / "skills.jsonl"

    if not index_file.exists():
        print(f"Error: {index_file} not found", file=sys.stderr)
        print("Run 'atlas build' first to generate the index", file=sys.stderr)
        return 1

    # Load skills
    skills = []
    with open(index_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                skills.append(json.loads(line))

    print(f"Loaded {len(skills)} skills from index")

    # Cluster by content hash
    clusters = cluster_by_content_hash(skills)

    # Find duplicate clusters
    duplicate_clusters = {h: c for h, c in clusters.items() if len(c) > 1}

    print(f"\nFound {len(clusters)} unique content hashes")
    print(f"Found {len(duplicate_clusters)} duplicate clusters")

    if args.report and duplicate_clusters:
        print("\nDuplicate clusters:")
        for content_hash, cluster in sorted(duplicate_clusters.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n  Hash: {content_hash[:16]}... ({len(cluster)} skills)")
            for skill in cluster:
                trust = skill.get("trust_tier", "unknown")
                first_seen = skill.get("first_seen", "unknown")[:10]  # Just the date
                print(f"    - {skill['id']}")
                print(f"      trust_tier: {trust}, first_seen: {first_seen}")

    # Apply deduplication
    if not args.dry_run:
        print("\nApplying deduplication...")
        skills = apply_deduplication(skills)

        # Rewrite index
        print("Writing updated index...")
        with open(index_file, "w", encoding="utf-8") as f:
            for skill in sorted(skills, key=lambda s: s["id"]):
                f.write(json.dumps(skill, ensure_ascii=False, sort_keys=True))
                f.write("\n")

        canonical_count = compute_canonical_count(skills)
        print("✓ Deduplication complete")
        print(f"  Total skills: {len(skills)}")
        print(f"  Canonical skills: {canonical_count}")
        print(f"  Duplicate skills: {len(skills) - canonical_count}")
    else:
        print("\nDry run - no changes made")

    return 0


def cmd_check_refs(args):
    """Check external references in skills for dangling refs and deleted owners."""
    import json
    import logging
    from pathlib import Path

    from tools.atlas import check_refs

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    repo_root = Path.cwd()
    raw_dir = repo_root / "build" / "raw"

    if not raw_dir.exists():
        print(f"Error: {raw_dir} not found. Run 'atlas crawl' first.", file=sys.stderr)
        return 1

    # Find all skill files
    skill_files = list(raw_dir.glob("*.jsonl"))
    if not skill_files:
        print(f"No skill files found in {raw_dir}", file=sys.stderr)
        return 1

    print(f"Checking external references in {len(skill_files)} source(s)...")

    checker = check_refs.ReferenceChecker(timeout=args.timeout)
    total_skills = 0
    skills_with_dangling = 0
    total_refs = 0
    total_dangling = 0

    for skill_file in skill_files:
        source_id = skill_file.stem

        if args.source and source_id != args.source:
            continue

        with open(skill_file) as f:
            for line in f:
                skill_data = json.loads(line)
                total_skills += 1

                result = check_refs.check_skill_references(skill_data, checker)

                total_refs += len(result["external_refs"])
                total_dangling += len(result["dangling_refs"])

                if result["has_dangling"]:
                    skills_with_dangling += 1
                    if args.verbose:
                        print(f"\n⚠️  Dangling refs in {skill_data.get('path', 'unknown')}:")
                        for ref in result["dangling_refs"]:
                            print(f"  - {ref}")

    print(f"\n✓ Checked {total_skills} skill(s)")
    print(f"  Total external references: {total_refs}")
    print(f"  Dangling references: {total_dangling}")
    print(f"  Skills with dangling refs: {skills_with_dangling}")

    if args.check_owners:
        # Check source owners
        print("\nChecking source repository owners...")
        sources_file = repo_root / "index" / "sources.json"

        if not sources_file.exists():
            print(f"Warning: {sources_file} not found, skipping owner checks")
            return 0

        with open(sources_file) as f:
            sources_data = json.load(f)

        sources = sources_data.get("repositories", [])
        deleted_owners = []

        for source in sources:
            if args.source and source.get("id") != args.source:
                continue

            exists = check_refs.check_source_owner(source, checker)
            if not exists:
                deleted_owners.append(source.get("id"))
                print(f"  ⚠️  DELETED OWNER: {source.get('url')}")

        if deleted_owners:
            print(f"\n⚠️  WARNING: {len(deleted_owners)} source(s) have deleted owners!")
            print("These skills should be marked as 'dangling' and taken down.")
            return 1

    return 0 if skills_with_dangling == 0 else 1


def cmd_index(args):
    """Build the router SQLite database from skills.jsonl (S3-2)."""
    from pathlib import Path

    from tools.atlas import router

    repo_root = Path.cwd()
    skills_file = repo_root / "index" / "skills.jsonl"
    output_dir = repo_root / "build"
    output_db = output_dir / "router.sqlite"

    if not skills_file.exists():
        print(f"Error: {skills_file} not found", file=sys.stderr)
        print("Run 'atlas build' first to generate the index", file=sys.stderr)
        return 1

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build router database
    print(f"Building router database from {skills_file}...")
    count = router.build_router_db(skills_file, output_db)

    print(f"✓ Router database built: {output_db}")
    print(f"  Indexed {count} skills")

    return 0


def cmd_find(args):
    """Search for skills using the router (S3-2)."""
    import json
    from pathlib import Path

    from tools.atlas import router

    repo_root = Path.cwd()
    db_path = repo_root / "build" / "router.sqlite"

    if not db_path.exists():
        print(f"Error: {db_path} not found", file=sys.stderr)
        print("Run 'atlas index' first to build the router database", file=sys.stderr)
        return 1

    # Map license filter
    license_filter = None
    if args.license == "permissive":
        license_filter = "permissive"

    # Search
    result = router.search_skills(
        db_path=db_path,
        query=args.query,
        k=args.k,
        layer=args.layer,
        license_filter=license_filter,
        min_trust=args.min_trust,
    )

    # Output
    if args.json:
        output = {
            "query": result.query,
            "abstained": result.abstained,
            "results": [
                {
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    "install": m.install,
                    "url": m.url,
                    "content_hash": m.content_hash,
                    "trust_tier": m.trust_tier,
                    "license": m.license,
                    "security": m.security,
                    "alternatives_count": m.alternatives_count,
                    "why_matched": m.why_matched,
                    "score": m.score,
                }
                for m in result.results
            ],
            "note": result.note,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        print(f"Query: {result.query}")
        if result.abstained:
            print("⚠️  Low confidence - abstained")
        print(f"Found {len(result.results)} skill(s):\n")

        for i, match in enumerate(result.results, 1):
            print(f"{i}. {match.name}")
            print(f"   {match.description[:100]}...")
            print(f"   ID: {match.id}")
            print(f"   Trust: {match.trust_tier} | License: {match.license} | Security: {match.security}")
            print(f"   URL: {match.url}")
            print(f"   Score: {match.score}")
            if match.alternatives_count > 0:
                print(f"   Alternatives: {match.alternatives_count}")
            print()

        if result.results:
            print(result.note)

    return 0


def cmd_show(args):
    """Show details for a specific skill by ID (S3-2)."""
    import json
    from pathlib import Path

    from tools.atlas import router

    repo_root = Path.cwd()
    db_path = repo_root / "build" / "router.sqlite"

    if not db_path.exists():
        print(f"Error: {db_path} not found", file=sys.stderr)
        print("Run 'atlas index' first to build the router database", file=sys.stderr)
        return 1

    # Get skill
    skill = router.get_skill_by_id(db_path, args.id)

    if not skill:
        print(f"Error: Skill '{args.id}' not found", file=sys.stderr)
        return 1

    # Output
    if args.json:
        print(json.dumps(skill, indent=2, ensure_ascii=False))
    else:
        print(f"Skill: {skill['name']}")
        print(f"ID: {skill['id']}")
        print(f"Description: {skill['description']}")
        print(f"\nLayer: {skill['layer']}")
        print(f"Trust: {skill['trust_tier']}")
        print(f"License: {skill['license']}")
        print(f"Security: {skill['security']}")
        print(f"\nURL: {skill['url']}")
        print(f"Content Hash: {skill['content_hash']}")
        if skill["alternatives_count"] > 0:
            print(f"Alternatives: {skill['alternatives_count']}")
        if skill.get("canonical_id"):
            print(f"Canonical ID: {skill['canonical_id']}")

        print("\nInstall:")
        if skill["install"]["npx"]:
            print(f"  npx: {skill['install']['npx']}")
        if skill["install"]["gh"]:
            print(f"  gh: {skill['install']['gh']}")
        if skill["install"]["claude_plugin"]:
            print(f"  plugin: {skill['install']['claude_plugin']}")

    return 0


def main():
    """Main entry point for the atlas CLI."""
    parser = argparse.ArgumentParser(prog="atlas", description="Skill Atlas CLI - Manage the agent skills index")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate index data and schema")
    validate_parser.add_argument("--wording", action="store_true", help="Run wording lint checks (if available)")
    validate_parser.set_defaults(func=cmd_validate)

    # crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Crawl agent skills from sources")
    crawl_parser.add_argument("--source", help="Specific source ID to crawl")
    crawl_parser.add_argument("--all", action="store_true", help="Crawl all sources")
    crawl_parser.add_argument("--force", action="store_true", help="Force crawl even if unchanged")
    crawl_parser.set_defaults(func=cmd_crawl)

    # build command
    build_parser = subparsers.add_parser("build", help="Build index files from crawled data")
    build_parser.add_argument("--check-refs", action="store_true", help="Check external references (S2-5)")
    build_parser.set_defaults(func=cmd_build)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Generate statistics from the index")
    stats_parser.add_argument("--readme", action="store_true", help="Update README.md stats block from stats.json")
    stats_parser.set_defaults(func=cmd_stats)

    # lint-skill command
    lint_skill_parser = subparsers.add_parser("lint-skill", help="Lint a skill directory for frontmatter conformance")
    lint_skill_parser.add_argument("directory", help="Path to skill directory containing SKILL.md")
    lint_skill_parser.add_argument("--lenient", action="store_true", help="Use lenient parsing mode")
    lint_skill_parser.set_defaults(func=cmd_lint_skill)

    # lint-quality command
    lint_quality_parser = subparsers.add_parser("lint-quality", help="Lint a skill directory for quality issues")
    lint_quality_parser.add_argument("directory", help="Path to skill directory containing SKILL.md")
    lint_quality_parser.set_defaults(func=cmd_lint_quality)

    # sources command
    sources_parser = subparsers.add_parser("sources", help="Manage source repositories")
    sources_subparsers = sources_parser.add_subparsers(dest="sources_command", help="Source commands")

    # sources import subcommand
    import_parser = sources_subparsers.add_parser("import", help="Import sources from a JSON file")
    import_parser.add_argument("file", help="Path to JSON file with sources to import")
    import_parser.set_defaults(func=cmd_sources_import)

    # discover command
    discover_parser = subparsers.add_parser(
        "discover", help="Discover skill repositories from aggregator READMEs (tier-3 sources)"
    )
    discover_parser.add_argument(
        "mode",
        nargs="?",
        default="awesome",
        choices=["awesome"],
        help="Discovery mode (currently only 'awesome' is supported)",
    )
    discover_parser.add_argument(
        "-o", "--output", help="Output path for candidates.jsonl (default: build/candidates.jsonl)"
    )
    discover_parser.set_defaults(func=cmd_discover)

    # scan-security command
    scan_security_parser = subparsers.add_parser("scan-security", help="Scan a skill for security issues (S2-4)")
    scan_security_parser.add_argument("directory", help="Path to skill directory containing SKILL.md")
    scan_security_parser.add_argument(
        "--layer", choices=["source", "curated"], default="source", help="Layer to scan for (default: source)"
    )
    scan_security_parser.add_argument("--json", action="store_true", help="Output security field as JSON")
    scan_security_parser.set_defaults(func=cmd_scan_security)

    # gate command
    gate_parser = subparsers.add_parser("gate", help="Check if a skill meets gate requirements (S2-7)")
    gate_parser.add_argument("gate", choices=["source", "curated"], help="Gate to check")
    gate_parser.add_argument("skill_id", help="Skill ID to check")
    gate_parser.add_argument("--json", action="store_true", help="Output as JSON")
    gate_parser.set_defaults(func=cmd_gate)

    # check-curated-gate command (regression watcher)
    check_curated_gate_parser = subparsers.add_parser(
        "check-curated-gate", help="Check if curated skills still pass the gate (S2-7 regression watcher)"
    )
    check_curated_gate_parser.add_argument(
        "--dry-run", action="store_true", help="Report issues without updating index or creating GitHub issues"
    )
    check_curated_gate_parser.set_defaults(func=cmd_check_curated_gate)

    # dedup command
    dedup_parser = subparsers.add_parser("dedup", help="Analyze and apply deduplication to the index")
    dedup_parser.add_argument("--report", action="store_true", help="Show detailed duplicate cluster report")
    dedup_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    dedup_parser.set_defaults(func=cmd_dedup)

    # check-refs command
    check_refs_parser = subparsers.add_parser(
        "check-refs", help="Check external references for dangling refs and deleted owners (S2-5)"
    )
    check_refs_parser.add_argument("--source", help="Specific source ID to check")
    check_refs_parser.add_argument("--check-owners", action="store_true", help="Also check if source owners exist")
    check_refs_parser.add_argument(
        "--timeout", type=float, default=10.0, help="Network timeout in seconds (default: 10)"
    )
    check_refs_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    check_refs_parser.set_defaults(func=cmd_check_refs)

    # index command (S3-2)
    index_parser = subparsers.add_parser("index", help="Build router SQLite database from skills.jsonl (S3-2)")
    index_parser.set_defaults(func=cmd_index)

    # find command (S3-2)
    find_parser = subparsers.add_parser("find", help="Search for skills using FTS5 router (S3-2)")
    find_parser.add_argument("query", help="Search query string")
    find_parser.add_argument("-k", type=int, default=5, help="Number of results to return (default: 5)")
    find_parser.add_argument("--layer", choices=["curated", "source"], help="Filter by layer")
    find_parser.add_argument(
        "--license", choices=["permissive"], help="Filter by license (permissive = allow-list licenses)"
    )
    find_parser.add_argument(
        "--min-trust",
        choices=["official", "community", "unreviewed"],
        help="Minimum trust tier",
    )
    find_parser.add_argument("--json", action="store_true", help="Output as JSON")
    find_parser.set_defaults(func=cmd_find)

    # show command (S3-2)
    show_parser = subparsers.add_parser("show", help="Show details for a specific skill by ID (S3-2)")
    show_parser.add_argument("id", help="Skill ID to show")
    show_parser.add_argument("--json", action="store_true", help="Output as JSON")
    show_parser.set_defaults(func=cmd_show)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
