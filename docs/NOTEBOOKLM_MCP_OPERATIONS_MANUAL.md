# NotebookLM MCP Operations Manual

**Last Updated**: 2026-01-03

---

## Guardrail

```
┌─────────────────────────────────────────────┐
│  DEFAULT: MCP tools only                    │
│                                             │
│  UI fallback requires:                      │
│  1. MCP auth refresh attempt #1 → fail      │
│  2. MCP auth refresh attempt #2 → fail      │
│  3. Document reason in receipt              │
│                                             │
│  See: NOTEBOOKLM_UI_FALLBACK_PLAYBOOK.md    │
└─────────────────────────────────────────────┘
```

---

## Preflight Gate (MANDATORY)

Before any MCP work, verify auth is healthy:

```python
# Preflight check - MUST pass before proceeding
result = notebook_list(max_results=5)
assert result["count"] > 0, "Auth failed - see Auth Recovery below"
```

**If count = 0** or error returned:
1. Check `~/.notebooklm-mcp/auth.json` exists and is recent
2. If stale → run Auth Recovery below
3. **Restart Claude Code session** after auth fix (MCP connection is cached)

---

## Auth Recovery (Nuclear Option)

When MCP tools return 0 notebooks or auth errors despite valid-looking tokens:

**⚠️ CRITICAL: Close ALL sessions first (discovered 2026-01-03)**

Running multiple MCP hosts simultaneously OR having NotebookLM open in a browser causes rapid session invalidation. Google sees multiple "clients" and kills the session within minutes.

**Before auth, close ALL of these:**
- Claude Desktop (Cmd+Q, not just close window)
- Claude Code (quit terminal)
- Any browser tabs with NotebookLM open
- Any other apps using notebooklm-mcp

**Then run:**

```bash
# 1. Nuke cached auth and chrome profile
rm -rf ~/.notebooklm-mcp/chrome-profile ~/.notebooklm-mcp/auth.json

# 2. Re-authenticate (opens Chrome, extracts fresh tokens)
notebooklm-mcp-auth

# 3. CRITICAL: Restart Claude Code session
#    The MCP connection caches auth state - must restart to pick up new tokens
```

**Root cause** (discovered 2026-01-03): Stale `chrome-profile/` can cause auth to "succeed" but return wrong session, showing 0 notebooks even when account has many.

**Verification after recovery**:
```python
notebook_list(max_results=5)  # Should return count > 0
notebook_create(title="Auth Smoke Test")  # Should succeed
```

---

## Workflow: Create Deep Notebook with Sources

This documents the MCP-first workflow for creating a NotebookLM notebook, adding sources, running queries, and generating artifacts.

### Prerequisites

1. MCP server installed: `uv cache clean && uv tool install --force .`
2. Valid auth tokens in `~/.notebooklm-mcp/auth.json`
3. Source content prepared (bundles as text)

---

## Step 1: Verify Authentication

```python
# List notebooks to verify auth works
notebook_list(max_results=5)
```

**Expected**: List of notebooks with IDs

**If 401/403 error**:
1. Re-extract cookies from Chrome DevTools
2. Call `save_auth_tokens(cookies="<cookie_header>")`
3. Retry `notebook_list()`
4. If still fails after 2 attempts → UI fallback allowed

---

## Step 2: Create Notebook

```python
notebook_create(title="Project Name - Deep Notebook v0")
```

**Capture**:
- `notebook_id` (UUID)
- `url` (for browser access)

**Example output**:
```json
{
  "notebook_id": "c0b11752-c427-4191-ac73-5dc27b879750",
  "title": "C017_brain-on-tap - Deep Notebook v0",
  "url": "https://notebooklm.google.com/notebook/c0b11752-c427-4191-ac73-5dc27b879750"
}
```

---

## Step 3: Add Sources (5 Bundles)

For each bundle, call `notebook_add_text`:

```python
# Bundle 1: OVERVIEW + QUICKSTART
notebook_add_text(
    notebook_id="<notebook_id>",
    text="# Bundle 1: Overview + Quickstart\n\n<content>",
    title="Bundle 1 - Overview + Quickstart"
)

# Bundle 2: TABS (7 GUI tabs)
notebook_add_text(
    notebook_id="<notebook_id>",
    text="# Bundle 2: GUI Tabs\n\n<content>",
    title="Bundle 2 - GUI Tabs"
)

# Bundle 3: ARCHITECTURE + OPERATIONS
notebook_add_text(
    notebook_id="<notebook_id>",
    text="# Bundle 3: Architecture + Operations\n\n<content>",
    title="Bundle 3 - Architecture + Operations"
)

# Bundle 4: CODE_TOUR + ILLUSTRATION_BRIEF
notebook_add_text(
    notebook_id="<notebook_id>",
    text="# Bundle 4: Code Tour + Illustration Brief\n\n<content>",
    title="Bundle 4 - Code Tour + Illustration"
)

# Bundle 5: OPEN_QUESTIONS + SECURITY_AND_PRIVACY
notebook_add_text(
    notebook_id="<notebook_id>",
    text="# Bundle 5: Open Questions + Security\n\n<content>",
    title="Bundle 5 - Open Questions + Security"
)
```

**Capture for each**:
- `source_id` (UUID)
- Confirmation message

---

## Step 4: Verify Notebook State

```python
notebook_get(notebook_id="<notebook_id>")
```

**Verify**:
- `sources` array has 5 entries
- Each source has `source_id` and `title`

---

## Step 5: Run Verification Query

```python
notebook_query(
    notebook_id="<notebook_id>",
    query="What are the key functions in engine.py and what does each one do?"
)
```

**Capture**:
- Full response text
- Any citations returned

**Expected format**:
```json
{
  "response": "The key functions in engine.py are:\n- load_fragments()...",
  "citations": [...],
  "conversation_id": "..."
}
```

---

## Step 6: Generate Mind Map Artifact

```python
# Requires confirmation
mind_map_create(
    notebook_id="<notebook_id>",
    title="System Architecture Mind Map",
    confirm=True  # Required!
)
```

**Capture**:
- `artifact_id`
- Generation status

**Then check status**:
```python
studio_status(notebook_id="<notebook_id>")
```

---

## Step 7: Create Receipt

Create file: `20_receipts/YYYY-MM-DD_notebooklm_<notebook_name>.md`

**Required fields**:
```markdown
# NotebookLM Receipt

**Date**: YYYY-MM-DD
**Notebook ID**: <uuid>
**URL**: https://notebooklm.google.com/notebook/<uuid>

## Sources Added
| # | Title | Source ID |
|---|-------|-----------|
| 1 | Bundle 1 - Overview | <uuid> |
...

## Verification Query
**Query**: "..."
**Response**: "..."

## Artifacts Generated
| Type | Title | Status |
|------|-------|--------|
| Mind Map | System Architecture | Complete |
```

---

## Quick Reference: Common Operations

| Operation | Tool | Confirm Required |
|-----------|------|------------------|
| List notebooks | `notebook_list` | No |
| Create notebook | `notebook_create` | No |
| Add text source | `notebook_add_text` | No |
| Add URL source | `notebook_add_url` | No |
| Query notebook | `notebook_query` | No |
| Generate mind map | `mind_map_create` | **Yes** |
| Generate audio | `audio_overview_create` | **Yes** |
| Delete notebook | `notebook_delete` | **Yes** |
| Delete source | `source_delete` | **Yes** |

---

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| 401 Unauthorized | Stale cookies | Re-extract from Chrome DevTools |
| 403 Forbidden | Invalid CSRF | Re-save auth tokens |
| Empty response | Session expired | Full auth refresh |
| Rate limit | Too many requests | Wait 24 hours (free tier) |

---

## See Also

- `NOTEBOOKLM_UI_FALLBACK_PLAYBOOK.md` - When MCP fails
- `NOTEBOOKLM_MCP_TOOL_AUDIT.md` - Complete tool reference
- `MCP_TEST_PLAN.md` - Full test coverage
- `AUTHENTICATION.md` - Token extraction guide
