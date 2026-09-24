#!/usr/bin/env python3
"""Atlas CLI - Skill Atlas management tool."""

import argparse
import sys
from pathlib import Path


def cmd_validate(args):
    """Validate the index data and schema."""
    from tools.atlas.schema import validate_index

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
        result = build.build_index(raw_dir, sources_file, index_dir, repo_root)
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
    print("Stats not yet implemented")
    return 0


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
    build_parser.set_defaults(func=cmd_build)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Generate statistics from the index")
    stats_parser.set_defaults(func=cmd_stats)

    # lint-skill command
    lint_skill_parser = subparsers.add_parser("lint-skill", help="Lint a skill directory for frontmatter conformance")
    lint_skill_parser.add_argument("directory", help="Path to skill directory containing SKILL.md")
    lint_skill_parser.add_argument("--lenient", action="store_true", help="Use lenient parsing mode")
    lint_skill_parser.set_defaults(func=cmd_lint_skill)

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

    # dedup command
    dedup_parser = subparsers.add_parser("dedup", help="Analyze and apply deduplication to the index")
    dedup_parser.add_argument("--report", action="store_true", help="Show detailed duplicate cluster report")
    dedup_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    dedup_parser.set_defaults(func=cmd_dedup)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
