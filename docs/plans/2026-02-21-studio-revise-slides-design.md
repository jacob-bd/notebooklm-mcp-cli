# Design: Slide Deck Revision (`studio_revise`)

**Date:** 2026-02-21
**Status:** Approved
**Scope:** Slide decks only (the only artifact type that supports revision)

## Overview

NotebookLM added the ability to revise individual slides in an existing slide deck. The feature creates a **new** slide deck artifact with the requested changes applied — the original is not modified.

## Discovered RPC

- **RPC ID:** `KmcKPe`
- **Purpose:** Revise an existing slide deck with per-slide instructions

### Request Params

```
[[2], artifact_id, [[[slide_index, instruction], ...]]]
```

- `[2]` — version/mode indicator (always `[2]`)
- `artifact_id` — UUID of the existing slide deck to revise
- `slide_index` — **0-based** (slide 1 = index 0)
- `instruction` — text describing the desired change (e.g., "Make the title larger")
- Multiple `[index, instruction]` pairs can be passed in one call

### Response

Returns a new artifact with:
- New artifact_id
- Title with `" (2)"` appended (e.g., "My Deck (2)")
- Status `1` (in_progress) — poll with existing `gArtLc` (studio_status)
- Original deck settings preserved (focus prompt, language, format, length)

## Code Changes

### 1. `core/base.py`

Add constant:
```python
RPC_REVISE_SLIDE_DECK = "KmcKPe"
```

### 2. `core/studio.py`

Add method:
```python
def revise_slide_deck(
    self,
    artifact_id: str,
    slide_instructions: list[tuple[int, str]],  # [(0-based index, instruction), ...]
) -> dict | None
```

Params structure:
```python
params = [[2], artifact_id, [[list(pair) for pair in slide_instructions]]]
```

### 3. `services/studio.py`

Add function:
```python
def revise_artifact(
    client,
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list[dict],  # [{"slide": 1, "instruction": "..."}, ...]
) -> ReviseResult
```

Responsibilities:
- Validate artifact_id is non-empty
- Validate slide_instructions is non-empty
- Validate all slide numbers are >= 1
- Convert 1-based slide numbers to 0-based for the API
- Call `client.revise_slide_deck()`
- Return ReviseResult TypedDict

Add TypedDict:
```python
class ReviseResult(TypedDict):
    artifact_type: str      # "slide_deck"
    artifact_id: str        # new artifact UUID
    original_artifact_id: str
    status: str             # "in_progress"
    message: str
```

### 4. `mcp/tools/studio.py`

Add tool:
```python
@logged_tool()
def studio_revise(
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list,  # [{"slide": 1, "instruction": "..."}, ...]
    confirm: bool = False,
) -> dict
```

Confirmation preview shows slides_to_revise and note about creating a new artifact.

### 5. `cli/commands/studio.py`

Add subcommand:
```bash
nlm studio revise <artifact_id> \
  --slide 1 "Make the title larger" \
  --slide 3 "Remove the image"
```

## Documentation Updates

| File | Change |
|---|---|
| `CLAUDE.md` | Add `studio_revise` to MCP tools table |
| `docs/API_REFERENCE.md` | Add `KmcKPe` RPC documentation |
| `docs/MCP_CLI_TEST_PLAN.md` | Add Test 5.12 for studio_revise |
| `docs/MCP_GUIDE.md` | Add `studio_revise` to Studio tools (3→4) |
| `docs/CLI_GUIDE.md` | Add `nlm studio revise` command |
| `README.md` | Add "Revise slide decks" to features table |
| `src/notebooklm_tools/cli/ai_docs.py` | Add `studio revise` command reference |
| `src/notebooklm_tools/data/SKILL.md` | Add revision workflow |

## Validation Rules

| Check | Error |
|---|---|
| `artifact_id` empty | `ValidationError` |
| `slide_instructions` empty | `ValidationError` |
| Any `slide` < 1 | `ValidationError("Slide numbers are 1-based")` |
| API returns no artifact | `ServiceError` |

## Not In Scope

- Revising other artifact types — only slides support revision
- In-place modification — the API creates a new artifact by design
- Undo/revert — NotebookLM does not support it

## Dev Process

Per project rules:
1. Add `revise_slide_deck()` to `core/studio.py`
2. Write Python test script to validate the RPC call works
3. Run test and confirm success
4. Add MCP tool and CLI command
5. Update all documentation
6. Reinstall: `uv cache clean && uv tool install --force .`
