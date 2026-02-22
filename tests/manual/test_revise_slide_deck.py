#!/usr/bin/env python3
"""Manual test: Revise a slide deck via RPC KmcKPe.

Usage:
    python tests/manual/test_revise_slide_deck.py <artifact_id>

The artifact_id must be an existing slide deck. This creates a NEW artifact
with the revision applied.
"""
import sys
from notebooklm_tools.core.client import NotebookLMClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/manual/test_revise_slide_deck.py <artifact_id>")
        sys.exit(1)

    artifact_id = sys.argv[1]
    print(f"Revising slide deck: {artifact_id}")
    print(f"Instruction: Slide 1 -> 'Make the title larger and bolder'")

    with NotebookLMClient() as client:
        result = client.revise_slide_deck(
            artifact_id=artifact_id,
            slide_instructions=[(0, "Make the title larger and bolder")],
        )

    if result:
        print(f"\n✓ Success!")
        print(f"  New artifact ID: {result['artifact_id']}")
        print(f"  Title: {result.get('title')}")
        print(f"  Status: {result['status']}")
        print(f"  Original: {result['original_artifact_id']}")
    else:
        print("\n✗ Failed — no result returned")
        sys.exit(1)

if __name__ == "__main__":
    main()
