# Slide Deck Revision (`studio_revise`) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the ability to revise individual slides in an existing slide deck, using the newly discovered `KmcKPe` RPC.

**Architecture:** Follow the existing layered pattern: add the RPC constant and core method in `core/`, add business logic and TypedDict in `services/studio.py`, add MCP tool in `mcp/tools/studio.py`, add CLI subcommand in `cli/commands/studio.py`. The API creates a **new** artifact (does not modify the original). Slide numbers are 1-based in the user interface but 0-based in the API.

**Tech Stack:** Python 3.11+, FastMCP, Typer, httpx (via existing `_call_rpc`)

**Design doc:** `docs/plans/2026-02-21-studio-revise-slides-design.md`

---

## Task 1: Add RPC Constant and Debug Name

**Files:**
- Modify: `src/notebooklm_tools/core/base.py:95` (after `RPC_GET_INTERACTIVE_HTML`)
- Modify: `src/notebooklm_tools/core/utils.py:39` (before closing `}` of `RPC_NAMES`)

**Step 1: Add RPC constant to `base.py`**

In `src/notebooklm_tools/core/base.py`, after line 95 (`RPC_GET_INTERACTIVE_HTML = "v9rmvd"`), add:

```python
    RPC_REVISE_SLIDE_DECK = "KmcKPe"  # Revise existing slide deck with per-slide instructions
```

**Step 2: Add debug name to `utils.py`**

In `src/notebooklm_tools/core/utils.py`, inside the `RPC_NAMES` dict (before the closing `}` on line 40), add:

```python
    "KmcKPe": "revise_slide_deck",
```

**Step 3: Verify no syntax errors**

Run: `python -c "from notebooklm_tools.core.base import BaseClient; print(BaseClient.RPC_REVISE_SLIDE_DECK)"`
Expected: `KmcKPe`

**Step 4: Commit**

```bash
git add src/notebooklm_tools/core/base.py src/notebooklm_tools/core/utils.py
git commit -m "feat: add RPC_REVISE_SLIDE_DECK constant (KmcKPe)"
```

---

## Task 2: Add `revise_slide_deck()` Method to Core

**Files:**
- Modify: `src/notebooklm_tools/core/studio.py` (add method after `rename_studio_artifact` at line 496)

**Step 1: Add the `revise_slide_deck` method**

In `src/notebooklm_tools/core/studio.py`, after the `rename_studio_artifact` method (after line 496), add:

```python
    def revise_slide_deck(
        self,
        artifact_id: str,
        slide_instructions: list[tuple[int, str]],
    ) -> dict | None:
        """Revise an existing slide deck with per-slide instructions.

        Creates a NEW slide deck artifact with the requested changes applied.
        The original artifact is not modified.

        Args:
            artifact_id: UUID of the existing slide deck to revise
            slide_instructions: List of (0-based_index, instruction) tuples.
                Each tuple specifies which slide to change and how.

        Returns:
            Dict with new artifact_id, title, and status, or None on failure
        """
        # RPC KmcKPe params: [[2], artifact_id, [[[slide_index, instruction], ...]]]
        instruction_pairs = [[idx, text] for idx, text in slide_instructions]
        params = [[2], artifact_id, [instruction_pairs]]

        result = self._call_rpc(
            self.RPC_REVISE_SLIDE_DECK,
            params,
        )

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            if isinstance(artifact_data, list) and len(artifact_data) > 0:
                new_artifact_id = artifact_data[0]
                title = artifact_data[2] if len(artifact_data) > 2 else None
                status_code = artifact_data[4] if len(artifact_data) > 4 else None

                return {
                    "artifact_id": new_artifact_id,
                    "title": title,
                    "original_artifact_id": artifact_id,
                    "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                }

        return None
```

**Step 2: Verify import works**

Run: `python -c "from notebooklm_tools.core.studio import StudioMixin; print(hasattr(StudioMixin, 'revise_slide_deck'))"`
Expected: `True`

**Step 3: Commit**

```bash
git add src/notebooklm_tools/core/studio.py
git commit -m "feat: add revise_slide_deck() core method"
```

---

## Task 3: Write Python Test Script and Validate RPC

**Files:**
- Create: `tests/manual/test_revise_slide_deck.py` (temporary test script)

**Step 1: Write the test script**

Create `tests/manual/test_revise_slide_deck.py`:

```python
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
```

**Step 2: Run the test**

Run: `uv run python tests/manual/test_revise_slide_deck.py <artifact_id>`

Replace `<artifact_id>` with a real slide deck artifact ID. Get one from:
```bash
nlm studio status <notebook_id>
```

Expected: Success message with new artifact ID, status "in_progress".

**Step 3: Commit**

```bash
git add tests/manual/test_revise_slide_deck.py
git commit -m "test: add manual test script for revise_slide_deck RPC"
```

---

## Task 4: Add Service Layer (`ReviseResult` + `revise_artifact()`)

**Files:**
- Modify: `src/notebooklm_tools/services/studio.py`
  - Add `ReviseResult` TypedDict after `RenameResult` (after line 71)
  - Add `revise_artifact()` function after `delete_artifact()` (after line 485)

**Step 1: Add the `ReviseResult` TypedDict**

In `src/notebooklm_tools/services/studio.py`, after the `RenameResult` class (after line 71), add:

```python
class ReviseResult(TypedDict):
    """Result of revising a slide deck."""
    artifact_type: str          # "slide_deck"
    artifact_id: str            # new artifact UUID
    original_artifact_id: str   # original artifact UUID
    status: str                 # "in_progress"
    message: str
```

**Step 2: Add the `revise_artifact()` function**

At the end of `src/notebooklm_tools/services/studio.py` (after the `delete_artifact` function), add:

```python
# ---------- Revise ----------

def revise_artifact(
    client: "NotebookLMClient",
    artifact_id: str,
    slide_instructions: list[dict],
) -> ReviseResult:
    """Revise a slide deck with per-slide instructions.

    Creates a NEW artifact — the original is not modified.

    Args:
        client: NotebookLM client
        artifact_id: UUID of the existing slide deck
        slide_instructions: List of dicts with 'slide' (1-based) and 'instruction' keys
            e.g. [{"slide": 1, "instruction": "Make the title larger"}]

    Returns:
        ReviseResult with new artifact details

    Raises:
        ValidationError: If inputs are invalid
        ServiceError: If API call fails
    """
    if not artifact_id:
        raise ValidationError("artifact_id is required")
    if not slide_instructions:
        raise ValidationError("slide_instructions must not be empty")

    # Validate and convert 1-based slide numbers to 0-based
    converted: list[tuple[int, str]] = []
    for item in slide_instructions:
        slide_num = item.get("slide")
        instruction = item.get("instruction", "")
        if not isinstance(slide_num, int) or slide_num < 1:
            raise ValidationError(
                f"Slide numbers must be integers >= 1 (got {slide_num!r}). "
                f"Slide numbers are 1-based (slide 1 = first slide)."
            )
        if not instruction:
            raise ValidationError(
                f"Instruction for slide {slide_num} must not be empty."
            )
        converted.append((slide_num - 1, instruction))  # 0-based for API

    try:
        result = client.revise_slide_deck(
            artifact_id=artifact_id,
            slide_instructions=converted,
        )
    except Exception as e:
        raise ServiceError(
            f"Failed to revise slide deck: {e}",
            user_message="Could not revise slide deck.",
        )

    if not result or not result.get("artifact_id"):
        raise ServiceError(
            "NotebookLM rejected slide deck revision — no artifact returned.",
            user_message=(
                "NotebookLM rejected slide deck revision. "
                "Verify the artifact_id is a valid slide deck and try again."
            ),
        )

    return ReviseResult(
        artifact_type="slide_deck",
        artifact_id=result["artifact_id"],
        original_artifact_id=artifact_id,
        status=result.get("status", "in_progress"),
        message="Slide deck revision started. A new artifact will be created.",
    )
```

**Step 3: Verify import works**

Run: `python -c "from notebooklm_tools.services.studio import revise_artifact, ReviseResult; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/notebooklm_tools/services/studio.py
git commit -m "feat: add revise_artifact() service function and ReviseResult"
```

---

## Task 5: Add MCP Tool (`studio_revise`)

**Files:**
- Modify: `src/notebooklm_tools/mcp/tools/studio.py` (add tool after `studio_delete`, after line 237)
- Modify: `src/notebooklm_tools/mcp/tools/__init__.py` (add import and export)

**Step 1: Add the `studio_revise` tool**

In `src/notebooklm_tools/mcp/tools/studio.py`, after the `studio_delete` function (after line 237), add:

```python


@logged_tool()
def studio_revise(
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list,
    confirm: bool = False,
) -> dict[str, Any]:
    """Revise individual slides in an existing slide deck. Creates a NEW artifact.

    Only slide decks support revision. The original artifact is not modified.
    Poll studio_status after calling to check when the new deck is ready.

    Args:
        notebook_id: Notebook UUID
        artifact_id: UUID of the existing slide deck to revise (from studio_status)
        slide_instructions: List of revision instructions, each with:
            - slide: Slide number (1-based, slide 1 = first slide)
            - instruction: Text describing the desired change
            Example: [{"slide": 1, "instruction": "Make the title larger"}]
        confirm: Must be True after user approval

    Example:
        studio_revise(
            notebook_id="abc",
            artifact_id="xyz",
            slide_instructions=[
                {"slide": 1, "instruction": "Make the title larger"},
                {"slide": 3, "instruction": "Remove the image"}
            ],
            confirm=True
        )
    """
    if not confirm:
        return {
            "status": "pending_confirmation",
            "message": "Please confirm before revising slide deck:",
            "settings": {
                "notebook_id": notebook_id,
                "artifact_id": artifact_id,
                "slides_to_revise": [
                    f"Slide {s.get('slide', '?')}: {s.get('instruction', '')}"
                    for s in slide_instructions
                ] if slide_instructions else [],
            },
            "note": "This creates a NEW slide deck with revisions applied. The original is not modified. Set confirm=True after user approves.",
        }

    try:
        client = get_client()
        result = studio_service.revise_artifact(
            client, artifact_id, slide_instructions,
        )
        return {
            "status": "success",
            "notebook_url": f"https://notebooklm.google.com/notebook/{notebook_id}",
            **result,
        }
    except (ValidationError, ServiceError) as e:
        return {"status": "error", "error": e.user_message if isinstance(e, ServiceError) else str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

**Step 2: Register in `__init__.py`**

In `src/notebooklm_tools/mcp/tools/__init__.py`:

1. Update the import from `.studio` (line 32-36) to add `studio_revise`:

```python
from .studio import (
    studio_create,
    studio_status,
    studio_delete,
    studio_revise,
)
```

2. Update the `__all__` list in the Studio section (lines 75-78) to add `"studio_revise"`:

```python
    # Studio (4 - consolidated create + revise)
    "studio_create",
    "studio_status",
    "studio_delete",
    "studio_revise",
```

**Step 3: Verify import works**

Run: `python -c "from notebooklm_tools.mcp.tools import studio_revise; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/notebooklm_tools/mcp/tools/studio.py src/notebooklm_tools/mcp/tools/__init__.py
git commit -m "feat: add studio_revise MCP tool"
```

---

## Task 6: Add CLI Subcommand (`nlm slides revise`)

**Files:**
- Modify: `src/notebooklm_tools/cli/commands/studio.py` (add `revise` command to `slides_app`, after the `create_slides` function ending at line 397)

**Step 1: Add the `revise` subcommand**

In `src/notebooklm_tools/cli/commands/studio.py`, after the `create_slides` function (after line 397), add:

```python


@slides_app.command("revise")
def revise_slides(
    artifact_id: str = typer.Argument(..., help="Artifact ID of the slide deck to revise"),
    slide: list[str] = typer.Option(
        ..., "--slide",
        help='Slide revision in format: SLIDE_NUM "instruction" (e.g., --slide 1 "Make title larger")',
    ),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Revise individual slides in an existing slide deck.

    Creates a NEW slide deck with revisions applied. The original is not modified.

    Examples:
        nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm
        nlm slides revise <artifact-id> --slide '1 Make title larger' --slide '3 Remove the image' --confirm
    """
    artifact_id = get_alias_manager().resolve(artifact_id)

    # Parse --slide arguments: each is "NUMBER instruction text"
    instructions: list[dict] = []
    for s in slide:
        parts = s.strip().split(None, 1)
        if len(parts) < 2:
            console.print(f"[red]Error:[/red] Invalid --slide format: '{s}'. Expected: NUMBER \"instruction\"")
            raise typer.Exit(1)
        try:
            slide_num = int(parts[0])
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid slide number: '{parts[0]}'. Must be an integer >= 1.")
            raise typer.Exit(1)
        instructions.append({"slide": slide_num, "instruction": parts[1]})

    if not confirm:
        console.print("[bold]Slides to revise:[/bold]")
        for inst in instructions:
            console.print(f"  Slide {inst['slide']}: {inst['instruction']}")
        console.print("\n[dim]This creates a NEW slide deck. The original is not modified.[/dim]")
        typer.confirm("Proceed with revision?", abort=True)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Revising slide deck...", total=None)
            with get_client(profile) as client:
                result = studio_service.revise_artifact(
                    client, artifact_id, instructions,
                )

        console.print("[green]✓[/green] Slide deck revision started")
        console.print(f"  New Artifact ID: {result.get('artifact_id', 'unknown')}")
        console.print(f"  Original: {artifact_id}")
        console.print(f"\n[dim]Run 'nlm studio status <notebook-id>' to check progress.[/dim]")
    except (ValidationError, ServiceError) as e:
        msg = e.user_message if isinstance(e, ServiceError) else str(e)
        console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
```

**Step 2: Verify the CLI command is registered**

Run: `uv cache clean && uv tool install --force . 2>&1 | tail -1`
Then: `nlm slides --help`
Expected: Shows both `create` and `revise` subcommands.

**Step 3: Commit**

```bash
git add src/notebooklm_tools/cli/commands/studio.py
git commit -m "feat: add 'nlm slides revise' CLI command"
```

---

## Task 7: Live Test MCP Tool and CLI

**Step 1: Reinstall package**

Run: `uv cache clean && uv tool install --force .`

**Step 2: Test CLI help**

Run: `nlm slides revise --help`
Expected: Shows usage with `--slide` option and `--confirm`.

**Step 3: Test CLI with real artifact**

Get a slide deck artifact ID:
```bash
nlm studio status <notebook_id>
```

Run:
```bash
nlm slides revise <artifact_id> --slide '1 Make the title larger and bolder' --confirm
```

Expected: Success message with new artifact ID.

**Step 4: Verify new artifact appears**

Run: `nlm studio status <notebook_id>`
Expected: New slide deck artifact with "(2)" in the title, status in_progress or completed.

**Step 5: Commit (if any fixes needed)**

Only commit if fixes were made during testing.

---

## Task 8: Update Documentation — `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add `studio_revise` to the MCP Tools table**

In `CLAUDE.md`, after the `studio_delete` row (line 158), add:

```markdown
| `studio_revise` | Revise slides in an existing slide deck (creates new artifact, REQUIRES confirmation) |
```

**Step 2: Add `studio_revise` to the confirmation list**

After the `studio_delete` confirmation bullet (line 174), add:

```markdown
- `studio_revise` requires `confirm=True` - creates a new artifact with revisions applied
```

**Step 3: Update MCP server instructions in `mcp/server.py`**

In `src/notebooklm_tools/mcp/server.py`, update the `instructions` string (line 41) to add `studio_revise`:

After `- studio_create(type=audio|video|...): Create any artifact type`, add:
```
- studio_revise: Revise individual slides in an existing slide deck
```

**Step 4: Commit**

```bash
git add CLAUDE.md src/notebooklm_tools/mcp/server.py
git commit -m "docs: add studio_revise to CLAUDE.md and MCP server instructions"
```

---

## Task 9: Update Documentation — `docs/API_REFERENCE.md`

**Files:**
- Modify: `docs/API_REFERENCE.md`

**Step 1: Add to Known RPC IDs table**

In `docs/API_REFERENCE.md`, after the `rc3d8d` row (line 260), add:

```markdown
| `KmcKPe` | Revise Slide Deck | `[[2], artifact_id, [[[0-based_index, "instruction"], ...]]]` |
```

**Step 2: Add full RPC documentation section**

After the Studio RPCs section (around line 627, after the response structure documentation), add a new subsection:

```markdown
### `KmcKPe` - Revise Slide Deck

Revises individual slides in an existing slide deck. Creates a **new** artifact — the original is not modified.

#### Request
```python
params = [
    [2],                           # Version/mode indicator (always [2])
    artifact_id,                   # UUID of the existing slide deck
    [
        [                          # Array of slide revision instructions
            [0, "Make the title larger"],   # [0-based slide index, instruction text]
            [2, "Remove the image"],        # Multiple instructions supported
        ]
    ]
]
```

#### Response
Returns the same structure as `R7cb6c` (Create Studio Content):
- `result[0][0]` — New artifact UUID
- `result[0][2]` — Title (original title + " (2)")
- `result[0][4]` — Status code (1 = in_progress, 3 = completed)
- `result[0][20]` — Original artifact UUID

#### Notes
- Slide index is **0-based** (slide 1 = index 0)
- Multiple slides can be revised in one call
- Original deck settings (focus prompt, language, format, length) are preserved
- Poll with `gArtLc` (studio_status) for completion
- Only slide decks support revision (no other artifact types)
```

**Step 3: Commit**

```bash
git add docs/API_REFERENCE.md
git commit -m "docs: add KmcKPe (revise slide deck) to API_REFERENCE.md"
```

---

## Task 10: Update Documentation — `docs/MCP_CLI_TEST_PLAN.md`

**Files:**
- Modify: `docs/MCP_CLI_TEST_PLAN.md`

**Step 1: Update tool count**

Update line 3 from `29` to `30` consolidated MCP tools:
```markdown
**Purpose:** Verify all **30 consolidated MCP tools** work correctly.
```

Update the version header accordingly.

**Step 2: Add Test 5.12 for `studio_revise`**

After Test 5.11 (Rename Studio Artifact, around line 578), add:

```markdown
### Test 5.12 - Revise Slide Deck
**Tool:** `studio_revise`
**CLI:** `nlm slides revise <artifact_id> --slide '1 Make the title larger' --confirm`

**Prompt:**
```
Revise the slide deck artifact [artifact_id] in notebook [notebook_id]:
- slide_instructions: [{"slide": 1, "instruction": "Make the title larger and bolder"}]
- confirm: true
```

**Expected:**
- New artifact created with status "in_progress"
- New artifact_id returned (different from original)
- Original artifact unchanged
- **Verify:** Run `studio_status` — new deck appears with "(2)" suffix in title.
```

**Step 3: Update summary table**

In the summary table (around line 893-908), update the Studio row:
- Change `studio_create, studio_status, studio_delete` to `studio_create, studio_status, studio_delete, studio_revise`
- Change the Studio count from `3` to `4`
- Update Total from `29` to `30`

**Step 4: Commit**

```bash
git add docs/MCP_CLI_TEST_PLAN.md
git commit -m "docs: add Test 5.12 (studio_revise) to MCP_CLI_TEST_PLAN.md"
```

---

## Task 11: Update Documentation — `docs/MCP_GUIDE.md` and `docs/CLI_GUIDE.md`

**Files:**
- Modify: `docs/MCP_GUIDE.md`
- Modify: `docs/CLI_GUIDE.md`

**Step 1: Update `docs/MCP_GUIDE.md`**

In `docs/MCP_GUIDE.md`, update the Studio Content section header (line 80):

Change from `### Studio Content (3 tools)` to:
```markdown
### Studio Content (4 tools)
```

After the `studio_delete` row (line 86), add:

```markdown
| `studio_revise` | Revise slides in existing deck (requires `confirm=True`) |
```

**Step 2: Update `docs/CLI_GUIDE.md`**

In `docs/CLI_GUIDE.md`, in the Studio Content Creation section (after the slides create commands, after line 107), add:

```markdown
# Revise slides (creates new deck)
nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm
nlm slides revise <artifact-id> --slide '1 Fix title' --slide '3 Remove image' --confirm
```

**Step 3: Commit**

```bash
git add docs/MCP_GUIDE.md docs/CLI_GUIDE.md
git commit -m "docs: add studio_revise to MCP_GUIDE.md and CLI_GUIDE.md"
```

---

## Task 12: Update Documentation — `README.md`

**Files:**
- Modify: `README.md`

**Step 1: Add "Revise slide decks" to features table**

In `README.md`, after the "Create Studio Content" row (line 73), add a new row:

```markdown
| Revise slide decks | `nlm slides revise` | `studio_revise` |
```

**Step 2: Update the MCP Guide link**

Update line 84 from "All 29 MCP tools" to "All 30 MCP tools":
```markdown
- **[MCP Guide](docs/MCP_GUIDE.md)** — All 30 MCP tools with examples
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add slide deck revision to README.md features table"
```

---

## Task 13: Update Documentation — `ai_docs.py` and `SKILL.md`

**Files:**
- Modify: `src/notebooklm_tools/cli/ai_docs.py`
- Modify: `src/notebooklm_tools/data/SKILL.md`

**Step 1: Update `ai_docs.py` — Quick Reference table**

In `src/notebooklm_tools/cli/ai_docs.py`, after the `nlm slides` row (line 104), update it to include revise:

```python
| `nlm slides` | Create and revise slide decks (create, revise) |
```

**Step 2: Update `ai_docs.py` — Slides command section**

In the Slides section (around lines 404-418), after the Verb-First slides create commands, add:

```python
#### Revise Slides

**Noun-First:**
```bash
nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm
nlm slides revise <artifact-id> --slide '1 Fix title' --slide '3 Remove image' --confirm
# Creates a NEW slide deck with revisions applied. Original is not modified.
```
```

**Step 3: Update `ai_docs.py` — Studio Commands section**

In the Studio Commands section (around line 466-481), after the `studio delete` line, add:

```python
nlm slides revise <artifact-id> --slide '1 instruction' --confirm  # Revise slides
```

**Step 4: Update `SKILL.md` — Content Generation section**

In `src/notebooklm_tools/data/SKILL.md`, in the Content Generation (Studio) section (around line 238), after the `studio_create` unified creation table, add:

```markdown
**Revise Slides:** Use `studio_revise` to revise individual slides in an existing slide deck.
- Requires `artifact_id` (from `studio_status`) and `slide_instructions`
- Creates a NEW artifact — the original is not modified
- Slide numbers are 1-based (slide 1 = first slide)
- Poll `studio_status` after calling to check when the new deck is ready
```

**Step 5: Update `SKILL.md` — CLI Commands section**

In the CLI Commands section (around lines 299-302 for slides), add after the slides create line:

```markdown
nlm slides revise <artifact-id> --slide '1 Make the title larger' --confirm
# Creates a NEW deck with revisions. Original unchanged.
```

**Step 6: Commit**

```bash
git add src/notebooklm_tools/cli/ai_docs.py src/notebooklm_tools/data/SKILL.md
git commit -m "docs: add studio_revise to ai_docs.py and SKILL.md"
```

---

## Task 14: Reinstall and Final Verification

**Step 1: Reinstall**

Run: `uv cache clean && uv tool install --force .`

**Step 2: Verify CLI**

Run: `nlm slides revise --help`
Expected: Help text showing `--slide` and `--confirm` options.

**Step 3: Verify MCP tool registration**

Run: `python -c "from notebooklm_tools.mcp.tools import studio_revise; print(studio_revise.__doc__[:50])"`
Expected: First 50 chars of the docstring.

**Step 4: Run test suite**

Run: `uv run pytest`
Expected: All existing tests pass (no regressions).

**Step 5: Commit (if any fixes needed)**

Only commit if fixes were made during verification.

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | RPC constant + debug name | `core/base.py`, `core/utils.py` |
| 2 | Core `revise_slide_deck()` method | `core/studio.py` |
| 3 | Manual Python test script | `tests/manual/test_revise_slide_deck.py` |
| 4 | Service layer (`ReviseResult` + `revise_artifact()`) | `services/studio.py` |
| 5 | MCP tool (`studio_revise`) | `mcp/tools/studio.py`, `mcp/tools/__init__.py` |
| 6 | CLI subcommand (`nlm slides revise`) | `cli/commands/studio.py` |
| 7 | Live testing (MCP + CLI) | — |
| 8 | Docs: `CLAUDE.md` + `mcp/server.py` | `CLAUDE.md`, `mcp/server.py` |
| 9 | Docs: `API_REFERENCE.md` | `docs/API_REFERENCE.md` |
| 10 | Docs: `MCP_CLI_TEST_PLAN.md` | `docs/MCP_CLI_TEST_PLAN.md` |
| 11 | Docs: `MCP_GUIDE.md` + `CLI_GUIDE.md` | `docs/MCP_GUIDE.md`, `docs/CLI_GUIDE.md` |
| 12 | Docs: `README.md` | `README.md` |
| 13 | Docs: `ai_docs.py` + `SKILL.md` | `cli/ai_docs.py`, `data/SKILL.md` |
| 14 | Reinstall + final verification | — |
