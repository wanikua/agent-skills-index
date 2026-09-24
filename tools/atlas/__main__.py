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
    print("Crawl not yet implemented")
    return 0


def cmd_build(args):
    """Build the index files from crawled data."""
    print("Build not yet implemented")
    return 0


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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
