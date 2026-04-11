# Verb Wrapper Parameter Parity Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all verb wrappers that silently drop parameters, and add a test that prevents this from happening again.

**Architecture:** The CLI has two routing paths for every command (e.g., `nlm infographic create` and `nlm create infographic`). The verb wrappers in `verbs.py` call the target command functions directly as Python calls — which means any parameter not explicitly passed is silently dropped. This plan adds missing parameters to all verb wrappers and adds a parametric test that compares signatures to catch future drift.

**Tech Stack:** Python, Typer, pytest

---

### Task 1: Write the parameter parity test

**Files:**
- Create: `tests/cli/test_verbs_parity.py`

This test introspects verb wrapper functions and their target functions, verifying that every parameter accepted by the target is either passed by the verb wrapper or explicitly exempted.

- [ ] **Step 1: Create the parity test file**

```python
"""Test that verb wrappers pass all parameters their target functions accept.

When a verb wrapper calls a target function directly (not through Typer),
any parameter not explicitly passed gets the raw typer.Option default
(an OptionInfo object) instead of the resolved value. This test catches
missing parameters so they can't silently break CLI commands.
"""

import inspect

import pytest
import typer

# Map of (verb_wrapper_function, target_function, {params_to_skip})
# params_to_skip: parameters on the target that the verb intentionally
# does not expose (e.g. the verb always passes a fixed value).
VERB_TARGET_PAIRS: list[tuple[str, str, str, set[str]]] = []


def _collect_pairs():
    """Build the list of verb/target pairs by inspecting verbs.py imports and calls."""
    from notebooklm_tools.cli.commands import verbs

    # Import all target modules
    from notebooklm_tools.cli.commands import (
        alias,
        download,
        notebook,
        research,
        source,
        studio,
    )

    # Each entry: (verb_func_name, verb_func, target_func, skip_set)
    # skip_set contains params the verb handles differently (e.g. wraps in a list)
    pairs = [
        ("create_audio_verb", verbs.create_audio_verb, studio.create_audio, set()),
        ("create_video_verb", verbs.create_video_verb, studio.create_video, set()),
        ("create_report_verb", verbs.create_report_verb, studio.create_report, set()),
        ("create_infographic_verb", verbs.create_infographic_verb, studio.create_infographic, set()),
        ("create_slides_verb", verbs.create_slides_verb, studio.create_slides, set()),
        ("create_quiz_verb", verbs.create_quiz_verb, studio.create_quiz, set()),
        ("create_flashcards_verb", verbs.create_flashcards_verb, studio.create_flashcards, set()),
        ("create_data_table_verb", verbs.create_data_table_verb, studio.create_data_table, set()),
        ("create_mindmap_verb", verbs.create_mindmap_verb, studio.create_mindmap, set()),
        # add_source verbs: skip url/text/drive/youtube/file since each verb handles one type
        ("add_url_verb", verbs.add_url_verb, source.add_source, {"text", "drive", "youtube", "file", "title", "doc_type"}),
        ("add_text_verb", verbs.add_text_verb, source.add_source, {"url", "drive", "youtube", "file", "doc_type"}),
        ("add_drive_verb", verbs.add_drive_verb, source.add_source, {"url", "text", "youtube", "file"}),
        ("describe_notebook_verb", verbs.describe_notebook_verb, notebook.describe_notebook, set()),
        ("describe_source_verb", verbs.describe_source_verb, source.describe_source, set()),
        ("query_notebook_verb", verbs.query_notebook_verb, notebook.query_notebook, set()),
        ("content_source_verb", verbs.content_source_verb, source.get_source_content, set()),
        ("download_slides_verb", verbs.download_slides_verb, download.download_slide_deck, set()),
        ("delete_alias_verb", verbs.delete_alias_verb, alias.delete_alias, set()),
        ("research_start_verb", verbs.research_start_verb, research.start_research, set()),
    ]
    return pairs


def _get_target_params(func) -> set[str]:
    """Get parameter names from a function, excluding 'return' annotation."""
    sig = inspect.signature(func)
    return {
        name
        for name, param in sig.parameters.items()
        if param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY)
    }


def _get_call_args(func, target_func) -> set[str]:
    """Get keyword argument names that a verb wrapper passes to its target.

    Uses the AST to inspect the actual function call site, not regex.
    This avoids false positives from parameter annotations, local variable
    assignments, or typer.Option() declarations.
    """
    import ast
    import textwrap

    src = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(src)
    target_name = target_func.__name__

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == target_name
        ):
            return {kw.arg for kw in node.keywords if kw.arg is not None}
    return set()


_PAIRS = _collect_pairs()


@pytest.mark.parametrize(
    "verb_name,verb_func,target_func,skip_params",
    [(name, vf, tf, skip) for name, vf, tf, skip in _PAIRS],
    ids=[name for name, _, _, _ in _PAIRS],
)
def test_verb_passes_all_target_params(verb_name, verb_func, target_func, skip_params):
    """Every parameter on the target function must be passed by the verb wrapper.

    If a target function accepts a parameter (e.g. --style, --focus, --wait),
    the verb wrapper must either:
    1. Accept it as a CLI option and pass it through, OR
    2. Be listed in skip_params with a reason

    Failing this test means the verb wrapper silently drops a parameter,
    which causes the target to receive a raw OptionInfo object instead of
    the intended default value.
    """
    target_params = _get_target_params(target_func)
    verb_call_args = _get_call_args(verb_func, target_func)

    # The verb may rename params (e.g. 'notebook' -> 'notebook_id')
    # so we check what keyword args the verb passes, not its own param names
    missing = target_params - verb_call_args - skip_params

    assert not missing, (
        f"{verb_name} does not pass these parameters to {target_func.__name__}: "
        f"{missing}. Either add them to the verb wrapper or add to skip_params with a reason."
    )
```

- [ ] **Step 2: Run the test to verify it catches the existing bugs**

Run: `uv run pytest tests/cli/test_verbs_parity.py -v`

Expected: Multiple FAILs for the known missing parameters (style, focus, wait, auto_import, format, json_output, confirm).

---

### Task 2: Fix all verb wrappers in verbs.py

**Files:**
- Modify: `src/notebooklm_tools/cli/commands/verbs.py`

Fix all 13 parameter gaps found in the audit. Each fix adds the missing parameter to the verb wrapper function signature and passes it through to the target.

- [ ] **Step 1: Fix `create_infographic_verb` — add `style`**

```python
@create_app.command("infographic")
def create_infographic_verb(
    notebook: str = typer.Argument(..., help="Notebook ID or alias"),
    orientation: str | None = typer.Option(
        None, "--orientation", "-o", help="Orientation: landscape, portrait, square"
    ),
    detail: str | None = typer.Option(
        None, "--detail", "-d", help="Detail level: concise, standard, detailed"
    ),
    style: str | None = typer.Option(
        None,
        "--style",
        help="Visual style: auto_select, sketch_note, professional, bento_grid, editorial, instructional, bricks, clay, anime, kawaii, scientific",
    ),
    language: str | None = typer.Option(None, "--language", help="BCP-47 language code"),
    focus: str | None = typer.Option(None, "--focus", help="Optional focus topic"),
    source_ids: str | None = typer.Option(
        None, "--source-ids", "-s", help="Comma-separated source IDs"
    ),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Create an infographic."""
    create_infographic(
        notebook_id=notebook,
        orientation=orientation or "landscape",
        detail=detail or "standard",
        style=style or "auto_select",
        language=language or "",
        focus=focus or "",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile,
    )
```

- [ ] **Step 2: Fix `create_quiz_verb` — add `focus`**

Add to the function signature after `difficulty` (no `-f` short flag — it would conflict with `--force` in other commands on the same app):
```python
    focus: str | None = typer.Option(None, "--focus", help="Optional focus topic"),
```

Add to the function call:
```python
    create_quiz(
        notebook_id=notebook,
        count=count or 2,
        difficulty=difficulty or 2,
        focus=focus or "",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile,
    )
```

- [ ] **Step 3: Fix `create_flashcards_verb` — add `focus`**

Add to the function signature after `difficulty`:
```python
    focus: str | None = typer.Option(None, "--focus", help="Optional focus topic"),
```

Add to the function call:
```python
    create_flashcards(
        notebook_id=notebook,
        difficulty=difficulty or "medium",
        focus=focus or "",
        source_ids=source_ids,
        confirm=confirm,
        profile=profile,
    )
```

- [ ] **Step 4: Fix `add_url_verb` — add `wait` and `wait_timeout`**

Add to the function signature:
```python
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for source processing to complete"),
    wait_timeout: float = typer.Option(600.0, "--wait-timeout", help="Wait timeout in seconds"),
```

Add to the function call:
```python
    add_source(
        notebook, url=[url_arg], text=None, drive=None, youtube=None, file=None,
        wait=wait, wait_timeout=wait_timeout, profile=profile,
    )
```

- [ ] **Step 5: Fix `add_text_verb` — add `wait` and `wait_timeout`**

Add to the function signature:
```python
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for source processing to complete"),
    wait_timeout: float = typer.Option(600.0, "--wait-timeout", help="Wait timeout in seconds"),
```

Add to the function call:
```python
    add_source(
        notebook, url=None, text=text_arg, drive=None, youtube=None, file=None,
        title=title or "Pasted Text", wait=wait, wait_timeout=wait_timeout, profile=profile,
    )
```

- [ ] **Step 6: Fix `add_drive_verb` — add `wait` and `wait_timeout`**

Add to the function signature:
```python
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for source processing to complete"),
    wait_timeout: float = typer.Option(600.0, "--wait-timeout", help="Wait timeout in seconds"),
```

Add to the function call:
```python
    add_source(
        notebook, url=None, text=None, drive=document_id, youtube=None, file=None,
        title=title or f"Drive Document ({document_id[:8]}...)", doc_type=doc_type,
        wait=wait, wait_timeout=wait_timeout, profile=profile,
    )
```

- [ ] **Step 7: Fix `research_start_verb` — add `auto_import`**

Add to the function signature:
```python
    auto_import: bool = typer.Option(
        False, "--auto-import", help="Wait for research to complete and auto-import sources"
    ),
```

Add to the function call:
```python
    start_research(
        query=query, source=source, mode=mode, notebook_id=notebook_id,
        title=title, force=force, auto_import=auto_import, profile=profile,
    )
```

- [ ] **Step 8: Fix `download_slides_verb` — add `format`**

Add to the function signature:
```python
    format: str = typer.Option("pdf", "--format", "-f", help="Format: pdf, pptx"),
```

Add to the function call:
```python
    download_slide_deck(
        notebook_id=notebook, output=output, artifact_id=artifact_id,
        no_progress=no_progress, format=format,
    )
```

- [ ] **Step 9: Fix `delete_alias_verb` — add `confirm`**

```python
@delete_app.command("alias")
def delete_alias_verb(
    name: str = typer.Argument(..., help="Alias name"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete an alias."""
    delete_alias(name=name, confirm=confirm)
```

- [ ] **Step 10: Fix `describe_notebook_verb` — add `json_output`**

Add to the function signature:
```python
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
```

Add to the function call:
```python
    describe_notebook(notebook_id=notebook, json_output=json_output, profile=profile)
```

- [ ] **Step 11: Fix `describe_source_verb` — add `json_output`**

Add to the function signature:
```python
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
```

Add to the function call:
```python
    describe_source(source_id=source, json_output=json_output, profile=profile)
```

- [ ] **Step 12: Fix `query_notebook_verb` — add `json_output`**

Add to the function signature:
```python
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
```

Add to the function call:
```python
    query_notebook(
        notebook_id=notebook, question=question, json_output=json_output,
        conversation_id=conversation_id, source_ids=source_ids,
        profile=profile, timeout=timeout,
    )
```

- [ ] **Step 13: Fix `content_source_verb` — add `json_output`**

Add to the function signature:
```python
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
```

Add to the function call:
```python
    get_source_content(source_id=source, json_output=json_output, output=output, profile=profile)
```

- [ ] **Step 14: Update `test_verbs_defaults.py` — add infographic style default**

Add to `TestInfographicVerbDefaults`:
```python
    def test_style_default_is_valid(self):
        assert "auto_select" in constants.INFOGRAPHIC_STYLES.names
```

Add to the parametrize list in `TestAllVerbDefaultsConsistency`:
```python
            ("auto_select", constants.INFOGRAPHIC_STYLES),
```

- [ ] **Step 15: Run all tests**

Run: `uv run pytest tests/cli/ -v`

Expected: All PASS, including the new parity test.

- [ ] **Step 16: Verify the original bug is fixed**

Run: `uv cache clean && uv tool install --force .`

Then test: `nlm create infographic <notebook_id> --source-ids <source_id> --confirm`

Expected: Infographic creation starts successfully (no OptionInfo crash).

---

### Task 3: Update documentation

**Files:**
- Modify: `CHANGELOG.md` (if it exists)
- Modify: `CONTRIBUTING.md` (if it has CLI guidance)

- [ ] **Step 1: Check what docs exist**

Look for `CHANGELOG.md` and `CONTRIBUTING.md`.

- [ ] **Step 2: Add changelog entry**

Add entry for the verb wrapper parity fix under the next release, mentioning:
- Fixed: `nlm create infographic` crash when `--style` not specified (Issue #142)
- Fixed: Multiple verb wrapper commands missing parameters (`--focus`, `--wait`, `--auto-import`, `--format`, `--json`, `--confirm`)
- Added: Parameter parity test to prevent future verb/command parameter drift

- [ ] **Step 3: Update CONTRIBUTING.md if applicable**

Add a note to the contributing guide:
- When adding a new CLI option to a command function, also add it to the corresponding verb wrapper in `verbs.py`
- The `test_verbs_parity.py` test will catch any missing parameters in CI

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "fix: sync verb wrapper parameters and add parity test (Issue #142)"
```
