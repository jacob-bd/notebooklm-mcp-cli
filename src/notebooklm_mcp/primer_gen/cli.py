"""
CLI entry point for PROJECT_PRIMER.md generation.

Usage:
    generate-project-primer <repo_id>
    generate-project-primer <repo_id> --output /path/to/output.md
"""

import argparse
import sys
from pathlib import Path

from .generator import GenerationResult, generate_primer, resolve_repo_path


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate PROJECT_PRIMER.md for a repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    generate-project-primer C017_brain-on-tap
    generate-project-primer C021_notebooklm-mcp --output ~/primers/C021.md
    generate-project-primer /full/path/to/repo
        """,
    )
    parser.add_argument(
        "repo",
        help="Repository ID (e.g., C017_brain-on-tap) or full path",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output path (default: <repo>/PROJECT_PRIMER.md)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output except errors",
    )

    args = parser.parse_args()

    # Resolve repo path
    repo_input = args.repo
    repo_path: Path

    if "/" in repo_input or "\\" in repo_input:
        # Treat as path
        repo_path = Path(repo_input).resolve()
        if not repo_path.exists():
            print(f"Error: Path does not exist: {repo_path}", file=sys.stderr)
            return 1
    else:
        # Treat as repo_id
        resolved = resolve_repo_path(repo_input)
        if resolved is None:
            print(f"Error: Could not find repo: {repo_input}", file=sys.stderr)
            print("Searched in workspace root from notebook_map.yaml", file=sys.stderr)
            return 1
        repo_path = resolved

    # Generate primer
    result = generate_primer(repo_path, args.output)

    if not result.success:
        print(f"Error generating primer: {result.error}", file=sys.stderr)
        return 1

    if not args.quiet:
        _print_result(result)

    return 0


def _print_result(result: GenerationResult) -> None:
    """Print generation result summary."""
    print()
    print("=" * 60)
    print("PROJECT_PRIMER.md Generated")
    print("=" * 60)
    print()
    print(f"  Repo ID:       {result.repo_id}")
    # Show tier with detected if different
    if result.tier_detected != result.tier:
        print(f"  Tier:          {result.tier} (detected: {result.tier_detected})")
    else:
        print(f"  Tier:          {result.tier}")
    print(f"  Source docs:   {result.source_count}")
    print(f"  Repo SHA:      {result.repo_sha}")
    print()
    print(f"  Output:        {result.primer_path}")
    print(f"  Hash:          {result.primer_hash}")
    print(f"  Generated:     {result.generated_at}")

    # Print warnings if any
    if result.warnings:
        print()
        print("-" * 60)
        print("WARNINGS:")
        for warning in result.warnings:
            print(f"  ⚠  {warning}")

    print()
    print("-" * 60)
    print("Upload status: pending")
    print()
    print("Next steps:")
    print("  1. Review the generated primer")
    print("  2. Upload to ChatGPT/Claude/Gemini Project")
    print("  3. Add project instructions (see protocol spec)")
    print("-" * 60)


if __name__ == "__main__":
    sys.exit(main())
