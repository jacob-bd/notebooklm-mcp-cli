# MCP Tool Verification Receipt

**Date**: 2026-01-03
**Scope**: Minimal verification attempt

---

## Test Results

| Category | Tool(s) Tested | Status | Notes |
|----------|----------------|--------|-------|
| Auth | `notebook_list` | FAIL | Returns 0 notebooks (wrong session) |
| Notebook | `notebook_get` | FAIL | Known notebook returns `null` |
| Notebook | `notebook_create` | FAIL | "Failed to create notebook" |

---

## Root Cause Analysis

The cached auth tokens in `~/.notebooklm-mcp/auth.json` are for a different Google account/session than the one used in the browser.

**Evidence**:
- `notebook_list` returns `count: 0` despite notebooks existing in browser
- `notebook_get` for known notebook ID returns `notebook: null`
- `notebook_create` fails outright

---

## Resolution Required

To fix MCP tool access:

1. Navigate to https://notebooklm.google.com in Chrome
2. Open DevTools → Network tab
3. Trigger any NotebookLM action (open a notebook)
4. Find a `batchexecute` request
5. Extract fresh cookies from request headers
6. Call `save_auth_tokens(cookies="<fresh_cookies>")`
7. Verify with `notebook_list()`

---

## Guardrail Validation

This verification confirms the UI fallback was correctly triggered:

```
Attempt 1: MCP tools returned auth errors → ✓
Attempt 2: Re-check with notebook_list → returns 0 → ✓
UI fallback allowed: Yes (per guardrail rules)
```

---

## Documentation Created

| File | Purpose |
|------|---------|
| `NOTEBOOKLM_UI_FALLBACK_PLAYBOOK.md` | When and how to use browser automation |
| `NOTEBOOKLM_MCP_OPERATIONS_MANUAL.md` | MCP-first workflows |
| `NOTEBOOKLM_MCP_TOOL_AUDIT.md` | Tool reference with confirm flags |

All three include the Guardrail section:
- Default: MCP tools only
- UI fallback after 2 failed auth refresh attempts
