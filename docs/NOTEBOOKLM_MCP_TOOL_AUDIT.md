# NotebookLM MCP Tool Audit

**Last Updated**: 2026-01-03
**Total Tools**: 31

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

Before running any audit or MCP operation:

```python
# Must return count > 0
result = notebook_list(max_results=5)
if result["count"] == 0:
    # Auth is stale - see Auth Recovery below
    raise AuthError("Preflight failed")
```

---

## Auth Recovery (Nuclear Option)

```bash
rm -rf ~/.notebooklm-mcp/chrome-profile ~/.notebooklm-mcp/auth.json
notebooklm-mcp-auth
# THEN: Restart Claude Code session (MCP connection is cached)
```

---

## Category 1: Authentication

| Tool | Inputs | Outputs to Capture | Confirm | Gotchas |
|------|--------|-------------------|---------|---------|
| `save_auth_tokens` | `cookies` (required), `request_body`, `request_url` | Cache path, success message | No | CSRF/session auto-extracted; cookies expire ~2 weeks |

**Verification test**:
```python
save_auth_tokens(cookies="<from_chrome_devtools>")
# Then: notebook_list() to confirm auth works
```

---

## Category 2: Notebook Management

| Tool | Inputs | Outputs to Capture | Confirm | Gotchas |
|------|--------|-------------------|---------|---------|
| `notebook_list` | `max_results` (default 100) | List of `{notebook_id, title, url}` | No | Returns owned + shared notebooks |
| `notebook_create` | `title` (optional) | `notebook_id`, `url` | No | Empty title = "Untitled notebook" |
| `notebook_get` | `notebook_id` | Full details, sources array | No | Sources may be empty initially |
| `notebook_describe` | `notebook_id` | AI summary, suggested_topics | No | Requires sources to be ingested first |
| `notebook_rename` | `notebook_id`, `new_title` | Success confirmation | No | |
| `notebook_delete` | `notebook_id`, `confirm=True` | Deletion confirmation | **Yes** | IRREVERSIBLE |

**Verification test**:
```python
# 1. List
result = notebook_list(max_results=5)
# Capture: notebook count

# 2. Create
nb = notebook_create(title="MCP Audit Test")
# Capture: notebook_id, url

# 3. Get
details = notebook_get(notebook_id=nb["notebook_id"])
# Capture: sources count

# 4. Rename
notebook_rename(notebook_id=nb["notebook_id"], new_title="MCP Audit Test - Renamed")

# 5. Delete (cleanup)
notebook_delete(notebook_id=nb["notebook_id"], confirm=True)
```

---

## Category 3: Source Management

| Tool | Inputs | Outputs to Capture | Confirm | Gotchas |
|------|--------|-------------------|---------|---------|
| `notebook_add_text` | `notebook_id`, `text`, `title` | `source_id` | No | Max ~500KB per source |
| `notebook_add_url` | `notebook_id`, `url` | `source_id` | No | Works with YouTube URLs |
| `notebook_add_drive` | `notebook_id`, `document_id`, `title`, `doc_type` | `source_id` | No | `doc_type`: doc, slides, sheets, pdf |
| `source_describe` | `source_id` | AI summary, keywords | No | Source must be processed first |
| `source_list_drive` | `notebook_id` | Sources with `is_fresh` status | No | Use before `source_sync_drive` |
| `source_sync_drive` | `source_ids`, `confirm=True` | Sync confirmation | **Yes** | Only for stale Drive sources |
| `source_delete` | `source_id`, `confirm=True` | Deletion confirmation | **Yes** | IRREVERSIBLE |

**Verification test**:
```python
# Add text source
src = notebook_add_text(
    notebook_id="<id>",
    text="Test content for audit",
    title="Audit Test Source"
)
# Capture: source_id

# Describe source (may need to wait for processing)
source_describe(source_id=src["source_id"])

# Delete (cleanup)
source_delete(source_id=src["source_id"], confirm=True)
```

---

## Category 4: Querying

| Tool | Inputs | Outputs to Capture | Confirm | Gotchas |
|------|--------|-------------------|---------|---------|
| `notebook_query` | `notebook_id`, `query`, `source_ids` (optional), `conversation_id` (optional) | Response text, citations, conversation_id | No | Rate limited ~50/day (free tier) |
| `chat_configure` | `notebook_id`, `goal`, `custom_prompt`, `response_length` | Configuration confirmation | No | `goal`: default, learning_guide, custom |

**Verification test**:
```python
# Query (requires sources)
result = notebook_query(
    notebook_id="<id>",
    query="Summarize the main topics"
)
# Capture: response, citations, conversation_id
```

---

## Category 5: Research

| Tool | Inputs | Outputs to Capture | Confirm | Gotchas |
|------|--------|-------------------|---------|---------|
| `research_start` | `query`, `source` (web/drive), `mode` (fast/deep), `notebook_id` | Task ID, notebook_id | No | `deep` mode takes longer (~40 sources) |
| `research_status` | `notebook_id`, `poll_interval`, `max_wait`, `compact` | Status, discovered sources | No | Blocks until complete or timeout |
| `research_import` | `notebook_id`, `task_id`, `source_indices` | Import confirmation | No | Call after status=completed |

**Verification test**:
```python
# Start research
task = research_start(
    query="NotebookLM best practices",
    source="web",
    mode="fast",
    notebook_id="<id>"
)
# Capture: task_id

# Poll status
status = research_status(notebook_id="<id>", max_wait=60)
# Capture: discovered sources

# Import (if completed)
research_import(notebook_id="<id>", task_id=task["task_id"])
```

---

## Category 6: Studio Content Generation

**All require `confirm=True`**

| Tool | Inputs | Outputs to Capture | Gotchas |
|------|--------|-------------------|---------|
| `mind_map_create` | `notebook_id`, `source_ids`, `title`, `confirm` | Artifact ID | Fast generation |
| `mind_map_list` | `notebook_id` | List of mind maps | No confirm needed |
| `audio_overview_create` | `notebook_id`, `format`, `length`, `language`, `focus_prompt`, `confirm` | Artifact ID | Takes 2-5 min |
| `video_overview_create` | `notebook_id`, `format`, `visual_style`, `language`, `focus_prompt`, `confirm` | Artifact ID | Takes 5-10 min |
| `infographic_create` | `notebook_id`, `orientation`, `detail_level`, `language`, `focus_prompt`, `confirm` | Artifact ID | |
| `slide_deck_create` | `notebook_id`, `format`, `length`, `language`, `focus_prompt`, `confirm` | Artifact ID | |
| `report_create` | `notebook_id`, `report_format`, `custom_prompt`, `language`, `confirm` | Artifact ID | Formats: Briefing Doc, Study Guide, Blog Post, Create Your Own |
| `flashcards_create` | `notebook_id`, `difficulty`, `confirm` | Artifact ID | Difficulty: easy, medium, hard |
| `quiz_create` | `notebook_id`, `question_count`, `difficulty`, `confirm` | Artifact ID | |
| `data_table_create` | `notebook_id`, `description`, `language`, `confirm` | Artifact ID | |
| `studio_status` | `notebook_id` | All artifacts with status | No confirm |
| `studio_delete` | `notebook_id`, `artifact_id`, `confirm` | Deletion confirmation | **IRREVERSIBLE** |

**Verification test**:
```python
# Generate mind map (fastest artifact)
mm = mind_map_create(
    notebook_id="<id>",
    title="Audit Test Mind Map",
    confirm=True
)
# Capture: artifact_id

# Check status
status = studio_status(notebook_id="<id>")
# Capture: all artifacts

# List mind maps
maps = mind_map_list(notebook_id="<id>")
# Capture: mind map count
```

---

## Verification Summary Checklist

Run minimal verification for each category:

- [ ] **Auth**: `save_auth_tokens` → `notebook_list`
- [ ] **Notebook**: `notebook_create` → `notebook_get` → `notebook_delete`
- [ ] **Sources**: `notebook_add_text` → `source_delete`
- [ ] **Query**: `notebook_query` (on notebook with sources)
- [ ] **Studio**: `mind_map_create` → `studio_status`

**Full verification**: See `MCP_TEST_PLAN.md` for all 31 tools.

---

## Verification Receipt Template

After running verification:

```markdown
# MCP Tool Verification Receipt

**Date**: YYYY-MM-DD
**Scope**: [Minimal / Full]

## Results

| Category | Tool(s) Tested | Status | Notes |
|----------|----------------|--------|-------|
| Auth | save_auth_tokens, notebook_list | PASS | |
| Notebook | create, get, delete | PASS | |
| Sources | add_text, delete | PASS | |
| Query | notebook_query | PASS | |
| Studio | mind_map_create, status | PASS | |

## Artifacts Created
- Test notebook: <id> (deleted)
- Test source: <id> (deleted)

## Issues Found
- None / [describe]
```

---

## See Also

- `NOTEBOOKLM_MCP_OPERATIONS_MANUAL.md` - Standard workflows
- `NOTEBOOKLM_UI_FALLBACK_PLAYBOOK.md` - When MCP fails
- `MCP_TEST_PLAN.md` - Full test coverage
- `API_REFERENCE.md` - Low-level API details
