#!/usr/bin/env python3
"""
notebooklm-sync: Deterministic CLI for syncing docs to NotebookLM.

Usage:
    notebooklm-sync "My Notebook" file1.md file2.md
    notebooklm-sync "My Notebook" docs/*.md --audio
    notebooklm-sync --list  # List existing notebooks
"""

import argparse
import sys
from pathlib import Path

from .auth import load_cached_tokens
from .api_client import NotebookLMClient


def get_client() -> NotebookLMClient:
    """Get authenticated NotebookLM client."""
    tokens = load_cached_tokens()
    if not tokens:
        print("Error: No cached auth tokens found.", file=sys.stderr)
        print("Run 'notebooklm-mcp-auth' first to authenticate.", file=sys.stderr)
        sys.exit(1)

    return NotebookLMClient(
        cookies=tokens.cookies,
        csrf_token=tokens.csrf_token,
        session_id=tokens.session_id,
    )


def list_notebooks() -> None:
    """List all existing notebooks."""
    client = get_client()
    notebooks = client.list_notebooks()

    if not notebooks:
        print("No notebooks found.")
        return

    print(f"Found {len(notebooks)} notebook(s):\n")
    for nb in notebooks:
        print(f"  [{nb.id[:8]}...] {nb.title} ({nb.source_count} sources)")


def find_notebook_by_name(client: NotebookLMClient, name: str):
    """Find existing notebook by exact name match."""
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.title == name:
            return nb
    return None


def sync_files(
    notebook_name: str,
    files: list[Path],
    create_audio: bool = False,
    audio_focus: str = "",
) -> None:
    """Sync files to a NotebookLM notebook."""
    client = get_client()

    # Check if notebook exists
    notebook = find_notebook_by_name(client, notebook_name)

    if notebook:
        print(f"Found existing notebook: {notebook_name} ({notebook.source_count} sources)")
    else:
        print(f"Creating new notebook: {notebook_name}")
        notebook = client.create_notebook(notebook_name)
        if not notebook:
            print("Error: Failed to create notebook.", file=sys.stderr)
            sys.exit(1)
        print(f"Created notebook: {notebook.id}")

    # Add each file as a text source
    source_ids = []
    for file_path in files:
        if not file_path.exists():
            print(f"  Skipping (not found): {file_path}")
            continue

        content = file_path.read_text(encoding="utf-8")
        title = file_path.name

        print(f"  Adding: {title} ({len(content):,} chars)...", end=" ")
        result = client.add_text_source(notebook.id, content, title=title)

        if result:
            source_ids.append(result["id"])
            print("OK")
        else:
            print("FAILED")

    print(f"\nAdded {len(source_ids)}/{len(files)} sources to notebook.")

    # Create audio overview if requested
    if create_audio and source_ids:
        print("\nGenerating Audio Overview (this may take several minutes)...")
        audio_result = client.create_audio_overview(
            notebook.id,
            source_ids,
            format_code=1,  # Deep dive
            length_code=2,  # Default length
            focus_prompt=audio_focus,
        )

        if audio_result:
            print("Audio Overview generation started!")
            print(f"Check NotebookLM for progress: https://notebooklm.google.com/notebook/{notebook.id}")
        else:
            print("Failed to start Audio Overview generation.", file=sys.stderr)

    print(f"\nNotebook URL: https://notebooklm.google.com/notebook/{notebook.id}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="notebooklm-sync",
        description="Sync documentation files to NotebookLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List existing notebooks
    notebooklm-sync --list

    # Sync markdown files to a notebook
    notebooklm-sync "C012 Roundtable" docs/*.md

    # Sync and generate audio overview
    notebooklm-sync "C012 Roundtable" docs/*.md --audio

    # Sync with custom audio focus
    notebooklm-sync "Project Docs" *.md --audio --focus "Explain the architecture"
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing notebooks and exit",
    )
    parser.add_argument(
        "notebook_name",
        nargs="?",
        help="Name of the notebook (creates if doesn't exist)",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Files to add as sources (supports glob patterns)",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Generate Audio Overview after adding sources",
    )
    parser.add_argument(
        "--focus",
        default="",
        help="Focus prompt for Audio Overview (e.g., 'Explain the architecture')",
    )

    args = parser.parse_args()

    if args.list:
        list_notebooks()
        return

    if not args.notebook_name:
        parser.print_help()
        sys.exit(1)

    if not args.files:
        print("Error: No files specified.", file=sys.stderr)
        sys.exit(1)

    # Expand glob patterns (shell may not expand them on all platforms)
    expanded_files = []
    for f in args.files:
        if "*" in str(f):
            expanded_files.extend(Path(".").glob(str(f)))
        else:
            expanded_files.append(f)

    if not expanded_files:
        print("Error: No files found matching patterns.", file=sys.stderr)
        sys.exit(1)

    sync_files(
        args.notebook_name,
        expanded_files,
        create_audio=args.audio,
        audio_focus=args.focus,
    )


if __name__ == "__main__":
    main()
