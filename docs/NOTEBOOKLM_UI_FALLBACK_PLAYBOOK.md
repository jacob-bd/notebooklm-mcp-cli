# NotebookLM UI Fallback Playbook

**Last Updated**: 2026-01-03

---

## When to Use UI Fallback

**Default**: Use MCP tools. See `NOTEBOOKLM_MCP_OPERATIONS_MANUAL.md`.

**UI fallback allowed only when**:
1. MCP auth refresh attempted (re-extract cookies via Chrome DevTools)
2. Second attempt still fails with 401/403
3. Task is time-sensitive

---

## Why UI Was Used (2026-01-03 Session)

| Issue | Detail |
|-------|--------|
| Root cause | `~/.notebooklm-mcp/auth.json` had stale CSRF token |
| MCP tool behavior | `notebook_add_text` returned auth errors |
| Workaround | Browser automation via `claude-in-chrome` MCP |

---

## Click Sequence: Add Copied Text Source

### Prerequisites
- Tab open to NotebookLM notebook URL
- Get tabId via `tabs_context_mcp`

### Steps

```
1. SCREENSHOT to see current state
   computer(action="screenshot", tabId=XXX)

2. CLICK "Add source" button
   find(query="Add source button", tabId=XXX) → get ref
   computer(action="left_click", ref="ref_XX", tabId=XXX)

3. WAIT for dialog
   computer(action="wait", duration=1, tabId=XXX)
   computer(action="screenshot", tabId=XXX)

4. CLICK "Copied text" option
   read_page(tabId=XXX, filter="interactive") → find "Copied text" ref
   computer(action="left_click", ref="ref_XX", tabId=XXX)

5. WAIT for text area
   computer(action="wait", duration=1, tabId=XXX)

6. TYPE content (condensed bundle)
   computer(action="type", text="<bundle_content>", tabId=XXX)

7. CLICK "Insert" button
   find(query="Insert button", tabId=XXX) → get ref
   computer(action="left_click", ref="ref_XX", tabId=XXX)

8. VERIFY source added
   computer(action="wait", duration=2, tabId=XXX)
   computer(action="screenshot", tabId=XXX)
   - URL should no longer contain "?addSource=true"
   - Source count should increment
```

### Repeat for each bundle

---

## What Failed

| Attempt | Result |
|---------|--------|
| Coordinate-based clicks | Sometimes didn't register (timing issue) |
| Direct MCP `notebook_add_text` | 401 auth error |
| Clicking without wait | Dialog not ready |

## What Worked

| Technique | Why |
|-----------|-----|
| `read_page` + ref-based clicks | Reliable element targeting |
| 1-2 second waits after dialog open | Allows JS to initialize |
| URL change detection | Confirms dialog closed successfully |
| Screenshots after each action | Provides visual evidence |

---

## Receipt Capture

After completing UI workflow:

1. **Screenshot final state** showing source count
2. **Run verification query** via UI or MCP
3. **Generate one artifact** (mind map recommended - quick)
4. **Create receipt file** in `20_receipts/` with:
   - Notebook ID
   - Sources added (count and names)
   - Verification query + response
   - Artifact type generated

Example receipt: `20_receipts/2026-01-03_notebooklm_deep_notebook_v0.md`

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
└─────────────────────────────────────────────┘
```

---

## Auth Recovery (Nuclear Option)

Before resorting to UI fallback, try the nuclear auth reset:

```bash
# 1. Nuke cached auth and chrome profile
rm -rf ~/.notebooklm-mcp/chrome-profile ~/.notebooklm-mcp/auth.json

# 2. Re-authenticate
notebooklm-mcp-auth

# 3. CRITICAL: Restart Claude Code session
#    MCP connection caches auth state
```

**Only proceed to UI fallback if**:
1. Nuclear reset completed
2. Claude Code session restarted
3. `notebook_list()` still returns 0 or errors

---

## See Also

- `NOTEBOOKLM_MCP_OPERATIONS_MANUAL.md` - MCP-first workflow
- `AUTHENTICATION.md` - Token extraction guide
- `NOTEBOOKLM_MCP_TOOL_AUDIT.md` - Tool reference
