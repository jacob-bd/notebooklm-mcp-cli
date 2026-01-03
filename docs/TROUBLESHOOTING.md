# Troubleshooting Guide

Common issues encountered when using the NotebookLM MCP server, with solutions.

## Authentication Issues

### Symptom: `notebook_list` returns 0 notebooks

**Cause:** Auth tokens have expired or rotated.

**Diagnosis:**
```python
notebook_list()  # Returns count: 0, notebooks: []
```

If you previously had notebooks and now see 0, auth is dead.

**Solution:**
1. Close all NotebookLM tabs in Chrome
2. Close any other MCP clients using NotebookLM
3. Run auth refresh:
   ```bash
   notebooklm-mcp-auth
   ```
4. **Restart Claude Code** (or restart MCP server) - tokens are cached at startup

### Symptom: Auth CLI shows success but API still fails

**Cause:** MCP server hasn't reloaded the new tokens from `~/.notebooklm-mcp/auth.json`.

**Solution:**
1. Verify tokens were written:
   ```bash
   cat ~/.notebooklm-mcp/auth.json | head -c 200
   ```
2. Restart Claude Code to reload MCP server
3. Retry `notebook_list()` to verify

### Symptom: Auth expires quickly during heavy usage

**Cause:** NotebookLM's free tier appears to rotate cookies after ~20-30 API calls.

**Pattern observed:**
| API Calls | Auth Status |
|-----------|-------------|
| 0-5 | Usually stable |
| 10-20 | May rotate |
| 25+ | High rotation risk |

**Mitigation:**
- Batch related operations together
- Check auth health (`notebook_list`) before long operations
- Keep `notebooklm-mcp-auth` ready for quick refresh

### Recovery Ladder (Auth Dies Mid-Operation)

1. **Stop current operation** - don't retry blindly
2. **Verify auth state:** `notebook_list()` - if 0, auth is dead
3. **Refresh auth:** Close Chrome tabs → `notebooklm-mcp-auth`
4. **Restart MCP:** Exit and restart Claude Code
5. **Verify recovery:** `notebook_list()` should return your notebooks
6. **Resume operation** - check `notebook_get()` to verify state before continuing

## Studio Artifact Issues

### Symptom: `video_overview_create` fails with "No sources found"

**Cause:** API quirk - sometimes fails even when sources exist.

**Solution:**
1. Verify sources exist: `notebook_get(notebook_id)`
2. Retry the video creation - often works on second attempt
3. If still failing, try a different artifact type first, then retry video

### Symptom: Quiz appears as "flashcards" in `studio_status`

**Cause:** API returns `type: flashcards` for quiz artifacts.

**Workaround:**
- Track artifacts by ID, not just type
- Quiz artifacts have `flashcard_count` populated (confusingly)

### Symptom: Mind maps don't appear in `studio_status`

**Cause:** Mind maps are stored separately from studio artifacts.

**Solution:**
```python
# Use mind_map_list instead of studio_status
mind_map_list(notebook_id)
```

### Symptom: `studio_status` shows artifacts but URLs are null

**Cause:** Artifacts still generating.

**Solution:**
- Poll `studio_status` periodically
- Check `status` field: `in_progress` vs `completed`
- URLs only populate after `status: completed`

## Source Management Issues

### Symptom: `source_sync_drive` has no effect

**Cause:** Only works for Google Drive sources, not pasted text.

**Check first:**
```python
source_list_drive(notebook_id)
# Look at "syncable_sources" vs "other_sources"
```

Pasted text sources appear in `other_sources` and cannot be synced.

### Symptom: Large text fails to add

**Cause:** NotebookLM has size limits per source.

**Workaround:**
- Split large documents into multiple sources
- Each source should be under ~50KB of text

## Query Issues

### Symptom: `notebook_query` returns generic answers

**Cause:** Query may not match source content well.

**Solutions:**
- Use specific terminology from your sources
- Reference document names in query
- Try rephrasing with different keywords

### Symptom: Queries return stale conversation_id

**Cause:** Conversation context from previous queries.

**Solution:**
- For fresh context, don't pass `conversation_id`
- For follow-up questions, use the returned `conversation_id`

## General Debugging

### Check system health

```python
# 1. Auth health
notebook_list()  # Should return your notebooks

# 2. Specific notebook
notebook_get(notebook_id)  # Should return notebook details

# 3. Studio status
studio_status(notebook_id)  # Check artifact states

# 4. Mind maps (separate)
mind_map_list(notebook_id)
```

### Verbose logging

Check MCP server logs for detailed error messages:
- Look for HTTP status codes (401, 403 = auth issues)
- Look for "CSRF" errors (token rotation)
- Look for rate limit messages

## Known Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| Notes | Not implemented | Cannot save chat responses as notes |
| Sharing | Not implemented | Cannot share notebooks via MCP |
| Export | Not implemented | Cannot download content |
| Audio playback | URL only | Returns URL, doesn't play audio |
| Video playback | URL only | Returns URL, doesn't play video |

## Session Hygiene Best Practices

1. **Start sessions with health check:**
   ```python
   notebook_list()  # Verify auth
   ```

2. **Before long operations:**
   - Note current notebook state (`notebook_get`)
   - Have auth refresh ready

3. **After auth refresh:**
   - Always restart Claude Code
   - Verify with `notebook_list`

4. **Document operations:**
   - Create receipts for non-trivial changes
   - Record artifact IDs for later verification
