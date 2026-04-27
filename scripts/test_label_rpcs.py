#!/usr/bin/env python3
"""POC test script for label management RPCs.

Tests all discovered label RPCs before implementing in the main codebase.
Run with: uv run python scripts/test_label_rpcs.py

Requires: valid auth tokens from `nlm login`
"""

import json
import sys
import time

from notebooklm_tools.core.auth import load_cached_tokens
from notebooklm_tools.core.client import NotebookLMClient

# ─── Helpers ─────────────────────────────────────────────────────────────────


def ok(label: str, data=None):
    print(f"  ✓ {label}")
    if data is not None:
        if isinstance(data, (dict, list)):
            print(f"    {json.dumps(data, indent=2)[:300]}")
        else:
            print(f"    {str(data)[:200]}")


def fail(label: str, err):
    print(f"  ✗ {label}: {err}", file=sys.stderr)


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ─── Test client ─────────────────────────────────────────────────────────────


class LabelTestClient(NotebookLMClient):
    """Thin subclass to expose raw _call_rpc for RPC testing."""

    # Label RPCs discovered via Chrome DevTools
    RPC_LABEL_MANAGE = "agX4Bc"  # auto-label + create + list
    RPC_LABEL_MUTATE = "le8sX"  # rename + emoji + move source
    RPC_LABEL_DELETE = "GyzE7e"  # delete one or many labels
    RPC_USER_TIER = "ozz5Z"  # get subscription tier (fires on page load)

    def _notebook_path(self, notebook_id: str) -> str:
        return f"/notebook/{notebook_id}"

    def auto_label(self, notebook_id: str) -> list:
        """Auto-label all sources using AI."""
        params = [[2], notebook_id, None, None, []]
        result = self._call_rpc(
            self.RPC_LABEL_MANAGE, params, path=self._notebook_path(notebook_id)
        )
        # result[1] = list of [name, [[src_id], ...], label_id, emoji]
        return result[1] if result and len(result) > 1 else []

    def create_label(self, notebook_id: str, name: str, emoji: str = "") -> list:
        """Create a new empty label manually."""
        params = [[2], notebook_id, None, None, None, [[name, emoji]]]
        result = self._call_rpc(
            self.RPC_LABEL_MANAGE, params, path=self._notebook_path(notebook_id)
        )
        return result[1] if result and len(result) > 1 else []

    def list_labels(self, notebook_id: str) -> list:
        """List current labels (uses auto_label RPC with existing labels returned)."""
        return self.auto_label(notebook_id)

    def rename_label(self, notebook_id: str, label_id: str, new_name: str) -> bool:
        """Rename a label."""
        params = [[2], notebook_id, label_id, [[[new_name]]]]
        result = self._call_rpc(
            self.RPC_LABEL_MUTATE, params, path=self._notebook_path(notebook_id)
        )
        return result == [] or result is not None

    def set_label_emoji(self, notebook_id: str, label_id: str, emoji: str) -> bool:
        """Set or change the emoji on a label."""
        params = [[2], notebook_id, label_id, [[[None, emoji]]]]
        result = self._call_rpc(
            self.RPC_LABEL_MUTATE, params, path=self._notebook_path(notebook_id)
        )
        return result == [] or result is not None

    def move_source_to_label(self, notebook_id: str, label_id: str, source_id: str) -> bool:
        """Add/move a source to a label (multi-label: source can be in multiple)."""
        params = [[2], notebook_id, label_id, [[None, [[source_id]]]]]
        result = self._call_rpc(
            self.RPC_LABEL_MUTATE, params, path=self._notebook_path(notebook_id)
        )
        return result == [] or result is not None

    def delete_labels(self, notebook_id: str, label_ids: list[str]) -> bool:
        """Delete one or more labels (sources are preserved)."""
        params = [[2], notebook_id, label_ids]
        result = self._call_rpc(
            self.RPC_LABEL_DELETE, params, path=self._notebook_path(notebook_id)
        )
        return result == [] or result is not None


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    # Load auth
    tokens = load_cached_tokens()
    if not tokens:
        print("ERROR: No auth tokens found. Run `nlm login` first.", file=sys.stderr)
        sys.exit(1)

    client = LabelTestClient(
        cookies=tokens.cookies,
        csrf_token=tokens.csrf_token or "",
        session_id=tokens.session_id or "",
        build_label=tokens.build_label or "",
    )

    # Pick a notebook with 5+ sources for testing
    # Change this to a notebook ID you want to test with
    TEST_NOTEBOOK_ID = "fa4c8009-23c1-4c54-85cf-87990d7ed8a8"  # NLM MCP Sources Test Notebook

    section("1. AUTO-LABEL — AI generates categories from sources")
    try:
        labels = client.auto_label(TEST_NOTEBOOK_ID)
        if labels:
            ok(f"Auto-labeled: {len(labels)} labels created")
            for lbl in labels:
                name, sources, label_id, emoji = lbl[0], lbl[1], lbl[2], lbl[3]
                src_count = len(sources) if sources else 0
                ok(f"  '{emoji}{name}' — {src_count} sources — id: {label_id[:8]}...")
        else:
            ok("Auto-label returned empty (labels may already exist)")
    except Exception as e:
        fail("auto_label", e)
        labels = []

    # Use the first label for subsequent tests
    test_label = labels[0] if labels else None
    if not test_label:
        print("\nNo labels to work with — skipping mutation tests.")
        return

    test_label_name = test_label[0]
    test_label_id = test_label[2]
    test_source_ids = [s[0] for s in (test_label[1] or [])]

    section("2. RENAME LABEL")
    new_name = f"{test_label_name} (renamed)"
    try:
        result = client.rename_label(TEST_NOTEBOOK_ID, test_label_id, new_name)
        ok(f"Renamed '{test_label_name}' → '{new_name}'", result)
        time.sleep(0.5)
        # Rename back
        client.rename_label(TEST_NOTEBOOK_ID, test_label_id, test_label_name)
        ok(f"Reverted back to '{test_label_name}'")
    except Exception as e:
        fail("rename_label", e)

    section("3. SET EMOJI")
    try:
        result = client.set_label_emoji(TEST_NOTEBOOK_ID, test_label_id, "🧪")
        ok(f"Set emoji 🧪 on '{test_label_name}'", result)
        time.sleep(0.5)
        # Clear emoji back (empty string removes it)
        client.set_label_emoji(TEST_NOTEBOOK_ID, test_label_id, "")
        ok("Cleared emoji")
    except Exception as e:
        fail("set_label_emoji", e)

    section("4. CREATE NEW LABEL MANUALLY")
    created_label_id = None
    try:
        updated_labels = client.create_label(TEST_NOTEBOOK_ID, "Test Label POC", "🧪")
        # Find the newly created label
        new_label = next((lbl for lbl in updated_labels if lbl[0] == "Test Label POC"), None)
        if new_label:
            created_label_id = new_label[2]
            ok(f"Created label 'Test Label POC' — id: {created_label_id[:8]}...")
        else:
            ok("Create returned label list", [lbl[0] for lbl in updated_labels])
    except Exception as e:
        fail("create_label", e)

    section("5. MOVE SOURCE TO LABEL")
    if test_source_ids and labels and len(labels) > 1:
        target_label = labels[1]
        target_label_id = target_label[2]
        target_label_name = target_label[0]
        source_to_move = test_source_ids[0]
        try:
            result = client.move_source_to_label(TEST_NOTEBOOK_ID, target_label_id, source_to_move)
            ok(f"Moved source {source_to_move[:8]}... → '{target_label_name}'", result)
        except Exception as e:
            fail("move_source_to_label", e)
    else:
        print("  (skipped — need 2+ labels and at least 1 source)")

    section("6. DELETE LABEL (cleanup)")
    if created_label_id:
        try:
            result = client.delete_labels(TEST_NOTEBOOK_ID, [created_label_id])
            ok(f"Deleted 'Test Label POC' (id: {created_label_id[:8]}...)", result)
        except Exception as e:
            fail("delete_labels", e)
    else:
        print("  (skipped — no label was created in step 4)")

    section("SUMMARY")
    print("  All label RPC tests complete.")
    print("  Review output above for any failures.")
    print(f"\n  Notebook: {TEST_NOTEBOOK_ID}")
    print("  Note: labels were cleaned up. If anything looks wrong,")
    print("  re-run auto-label from the NotebookLM UI to reset.\n")


if __name__ == "__main__":
    main()
