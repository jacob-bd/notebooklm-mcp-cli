# NotebookLM CLI - Troubleshooting Guide

This document provides detailed solutions for common issues when using the `nlm` CLI.

## Quick Diagnosis

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| "Cookies have expired" | Session timeout | `nlm login` |
| "Notebook not found" | Invalid/stale ID | `nlm notebook list` |
| "Source not found" | Invalid source ID | `nlm source list <nb-id>` |
| Chrome doesn't open | Port conflict | Close existing Chrome, retry |
| "Research already in progress" | Pending task | `--force` or import existing |
| "nodename nor servname" | Network blocked | See [Sandbox Users](#sandbox-environments) |
| Commands hang forever | Network/auth issue | Ctrl+C, `nlm login` |

---

## Authentication Issues

### Session Expired

**Symptoms:**
```
Error: Cookies have expired. Please run 'nlm login' to re-authenticate.
Error: authentication may have expired
```

**Cause:** NotebookLM sessions last approximately 20 minutes.

**Solution:**
```bash
nlm login
```

**Prevention:** For long-running scripts, implement periodic re-authentication:
```bash
# Check auth before critical operations
nlm login --check || nlm login
```

### Chrome Doesn't Launch

**Symptoms:**
- `nlm login` hangs with no browser window
- Error about Chrome not found

**Solutions:**

1. **Ensure Chrome is installed and in PATH:**
   ```bash
   which google-chrome || which chromium
   # On macOS, Chrome is at /Applications/Google Chrome.app
   ```

2. **Close existing Chrome instances:**
   ```bash
   pkill -f "Chrome"
   # Wait a moment, then retry
   nlm login
   ```

3. **Port conflict (port 9222 in use):**
   The CLI automatically tries ports 9222-9231, but if all are blocked:
   ```bash
   lsof -i :9222
   # Kill the process using the port
   kill -9 <PID>
   ```

### Profile Issues

**Symptom:** "Profile not found" or wrong account being used.

**Solutions:**

1. **List existing profiles:**
   ```bash
   nlm login profile list
   ```

2. **Create a new profile:**
   ```bash
   nlm login --profile work
   ```

3. **Delete corrupted profile:**
   ```bash
   nlm login profile delete <profile-name>
   nlm login --profile <profile-name>
   ```

4. **Switch default profile:**
   ```bash
   nlm login switch <profile-name>
   ```

5. **Check current session:**
   ```bash
   nlm login --check
   ```

---

## Network Issues

### Sandbox Environments

**Symptom:**
```
Error: Request failed: [Errno 8] nodename nor servname provided, or not known
Hint: Check your internet connection.
```

**Cause:** Running inside a sandboxed environment (OpenAI Codex, containers) that blocks network access.

**Solution for OpenAI Codex:**

Add to `~/.codex/config.toml`:
```toml
[sandbox_workspace_write]
network_access = true
```

Or run with full network access:
```bash
codex exec --sandbox danger-full-access "nlm notebook list"
```

**Solution for Docker/Containers:**
Ensure the container has network access and can reach `notebooklm.google.com`.

### Rate Limiting

**Symptom:**
```
Error: Rate limit exceeded
```

**Cause:** Too many API calls in a short period. Free tier: ~50 queries/day.

**Solutions:**

1. **Wait and retry:**
   ```bash
   sleep 30
   # Retry command
   ```

2. **Implement throttling in scripts:**
   ```bash
   # Wait 2 seconds between operations
   nlm source add $ID --url "..." && sleep 2
   nlm source add $ID --url "..." && sleep 2
   ```

3. **Use batch operations where possible:**
   - Use `nlm research import` to import multiple sources at once
   - Use `nlm source sync` to sync all stale sources at once

---

## Source Issues

### Source Not Found

**Symptom:**
```
Error: Source not found
```

**Solutions:**

1. **Verify source exists:**
   ```bash
   nlm source list <notebook-id>
   ```

2. **Check correct notebook:**
   Sources are scoped to notebooks. Ensure you're using the right notebook ID.

3. **Source may have been deleted:**
   If the source was recently deleted, it no longer exists.

### Drive Source Issues

**Symptom:** Drive document fails to add or shows wrong content.

**Solutions:**

1. **Verify document ID:**
   Extract from URL: `https://docs.google.com/document/d/[DOC_ID]/edit`

2. **Specify correct type:**
   ```bash
   nlm source add <nb-id> --drive <doc-id> --type slides  # for Slides
   nlm source add <nb-id> --drive <doc-id> --type sheets  # for Sheets
   nlm source add <nb-id> --drive <doc-id> --type pdf     # for PDF
   ```

3. **Check permissions:**
   Ensure your Google account has access to the Drive document.

4. **Large documents timeout:**
   Very large documents (100+ slides) may take longer. The CLI has a 120-second timeout.

### Stale Drive Sources

**Symptom:** Drive source content is outdated.

**Solution:**
```bash
# Check which sources are stale
nlm source stale <notebook-id>

# Sync all stale sources
nlm source sync <notebook-id> --confirm

# Sync specific sources
nlm source sync <notebook-id> --source-ids <id1>,<id2> --confirm
```

---

## Research Issues

### Research Already in Progress

**Symptom:**
```
Error: Research already in progress
```

**Solutions:**

1. **Wait for completion:**
   ```bash
   nlm research status <notebook-id>
   ```

2. **Import existing results:**
   ```bash
   nlm research status <notebook-id> --full  # Get task ID
   nlm research import <notebook-id> <task-id>
   ```

3. **Force new research:**
   ```bash
   nlm research start "query" --notebook-id <id> --force
   ```

### Research Takes Too Long

**Expected durations:**
- Fast mode: ~30 seconds
- Deep mode: ~5 minutes

**If exceeding these times:**

1. **Check status without waiting:**
   ```bash
   nlm research status <notebook-id> --max-wait 0
   ```

2. **Try a more specific query:**
   Broader queries take longer. Narrow down the search terms.

---

## Generation Issues

### Artifact Still Generating

**Symptom:** `nlm studio status` shows "in_progress" for extended time.

**Expected generation times:**
- Reports, quizzes, flashcards: 30-60 seconds
- Audio podcasts: 2-5 minutes
- Videos: 3-7 minutes
- Deep research: 4-5 minutes

**Solution:** Keep polling:
```bash
nlm studio status <notebook-id>
```

### Generation Failed

**Symptom:** Artifact status shows "failed" or (✗).

**Possible causes and solutions:**

1. **No sources in notebook:**
   ```bash
   nlm source list <notebook-id>
   # If empty, add sources first
   ```

2. **Sources too short:**
   Add more substantial content to your sources.

3. **Retry generation:**
   ```bash
   # Delete failed artifact
   nlm studio delete <notebook-id> <artifact-id> --confirm
   # Regenerate
   nlm audio create <notebook-id> --confirm
   ```

### Missing --confirm Flag

**Symptom:**
```
Error: Missing required flag: --confirm
```

**Cause:** All generation and delete commands require explicit confirmation.

**Solution:** Add `--confirm` or `-y`:
```bash
nlm audio create <notebook-id> --confirm
# or
nlm audio create <notebook-id> -y
```

---

## Command Syntax Issues

### Wrong Argument Order

**Common mistakes:**

```bash
# WRONG: research start without --notebook-id
nlm research start "query" <notebook-id>

# CORRECT: --notebook-id is a required flag
nlm research start "query" --notebook-id <notebook-id>
```

```bash
# WRONG: data-table without description
nlm data-table create <notebook-id> --confirm

# CORRECT: description is required positional argument
nlm data-table create <notebook-id> "Extract all dates" --confirm
```

### Custom Chat Prompt Without --goal

**Symptom:**
```
Error: --prompt is required when goal is 'custom'
```

**Solution:**
```bash
# CORRECT: specify both --goal custom AND --prompt
nlm chat configure <id> --goal custom --prompt "Act as a tutor..."
```

---

## Getting More Help

1. **Check command help:**
   ```bash
   nlm <command> --help
   ```

2. **Get full AI documentation:**
   ```bash
   nlm --ai
   ```

3. **Check version:**
   ```bash
   nlm --version
   ```

4. **GitHub Issues:**
   https://github.com/jacob-bd/notebooklm-cli/issues
