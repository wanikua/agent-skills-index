#!/usr/bin/env python3
"""Atlas CLI - Skill Atlas management tool."""

import argparse
import sys
from pathlib import Path


def cmd_validate(args):
    """Validate the index data and schema."""
    if args.wording:
        wording_lint_path = Path(__file__).parent.parent.parent / "tools" / "wording_lint.py"
        if wording_lint_path.exists():
            import subprocess

            result = subprocess.run([sys.executable, str(wording_lint_path)], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Wording lint failed:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
                return 1
            print("Wording lint passed")
        else:
            print("Wording lint not available (tools/wording_lint.py not found), skipping")

    print("Validation not yet implemented")
    return 0


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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
