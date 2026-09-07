# Gemini Notebook (formerly Google NotebookLM) CLI - Troubleshooting Guide

This document provides detailed solutions for common issues when using the `nlm` CLI.

## Quick Diagnosis

| Symptom                                      | Likely Cause                | Quick Fix                                  |
| -------------------------------------------- | --------------------------- | ------------------------------------------ |
| "Cookies have expired" / auth status `stale` | Credentials rejected        | `nlm login`                                |
| Auth status `unverified`                     | Network/proxy probe failure | Check connectivity or try an API call      |
| "Notebook not found"                         | Invalid/stale ID            | `nlm notebook list`                        |
| "Source not found"                           | Invalid source ID           | `nlm source list <nb-id>`                  |
| Browser doesn't open                         | Port conflict               | Close existing browser, retry              |
| "Research already in progress"               | Pending task                | `--force` or import existing               |
| "nodename nor servname"                      | Network blocked             | See [Sandbox Users](#sandbox-environments) |
| Commands hang forever                        | Network/auth issue          | Ctrl+C, `nlm login`                        |

---

## Authentication Issues

### Session Expired

**Symptoms:**

```
Error: Cookies have expired. Please run 'nlm login' to re-authenticate.
Error: authentication may have expired
```

**Cause:** Gemini Notebook rejected the stored credentials. Cookies often remain
usable for weeks, so do not re-authenticate solely because time has passed.

**Solution:**

```bash
nlm login
```

**Prevention:** For long-running scripts, implement periodic re-authentication:

```bash
# Check auth before critical operations
nlm login --check || nlm login
```

**Unattended machines:** A live session self-heals — when the short-lived
cookies age out, the client runs a headless refresh automatically. To refresh
proactively from a scheduler (so a session never lapses between jobs), use:

```bash
nlm auth refresh          # Headless, no interaction; exits non-zero on failure
```

Run it on a timer (e.g. cron/launchd every 30 min). It needs a saved Chrome
profile from a prior `nlm login`, and does not apply when `NOTEBOOKLM_COOKIES`
is set as an environment variable (that value overrides saved credentials).

### Browser Doesn't Launch

**Symptoms:**

- `nlm login` hangs with no browser window
- Error about no supported browser found

**Solutions:**

1. **Ensure a supported Chromium-based browser is installed:**
   Supported browsers (in priority order): Google Chrome, Arc (macOS), Dia (macOS) Brave, Microsoft Edge, Chromium, Vivaldi, Opera.

   ```bash
   which google-chrome || which brave-browser || which chromium
   ```

2. **Close existing browser instances:**

   ```bash
   pkill -f "Chrome\|Brave\|Arc\|Edge"
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

### Proxy Environments

HTTP, HTTPS, and SOCKS proxy environment variables are supported. If a SOCKS
environment fails with a missing `socksio` import, upgrade or reinstall
`notebooklm-mcp-cli` 0.7.7 or newer. The client sanitizes only malformed
CIDR-style `no_proxy` entries; valid IPv6 loopback and `host:port` entries are
preserved.

### RPC Method-ID Drift

Gemini Notebook can rotate internal RPC method IDs without notice. When
`RPCDriftError` identifies a replacement:

1. Run the failing command with `--debug` and inspect the returned RPC IDs.
2. Set the suggested override, for example:
   ```bash
   export NOTEBOOKLM_RPC_OVERRIDES='{"RPC_LIST_NOTEBOOKS":"newId"}'
   ```
3. Restart the MCP server. CLI commands read the environment on their next
   invocation.

An entirely empty response has no RPC IDs to compare and may still return
without a drift diagnosis.

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
Ensure the container has network access and can reach `notebook.google.com`.

### Rate Limiting

**Symptom:**

```
Error: Rate limit exceeded
```

**Cause:** Too many API calls in a short period. Query and Studio generation
limits are separate and undocumented; video limits may require a longer pause.

**Solutions:**

1. **Wait and retry:**

   ```bash
   sleep 120  # Studio/video generation; shorter waits may be enough for queries
   # Retry command
   ```

   Built-in retries use a short 1/2/4-second backoff for transient failures.
   They do not wait through a minute-scale Studio quota window.

2. **Implement throttling in scripts:**

   ```bash
   # Run Studio/video creation sequentially; avoid parallel generation batches.
   # Wait 2 seconds between lightweight source operations.
   nlm source add $ID --url "..." && sleep 2
   nlm source add $ID --url "..." && sleep 2
   ```

3. **Use batch operations where possible:**
   - Use `nlm research import` to import multiple sources at once
   - Use `nlm source sync` to sync all stale sources at once

---

## Source Issues

### File Not Found During Upload

`source_add(source_type="file")` and `nlm source add --file` read files from
the machine running the MCP server or CLI. A path on a phone, browser, or
different agent host is not transferred automatically. Use a server-local
path. Errors include the underlying file reason and the received path.

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

When `--skip-freshness` / `-S` is used, `stale=null` means freshness was not
checked. It does not mean the source is fresh.

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

Deep research can take longer. MCP `research_status` and CLI auto-import wait
up to 15 minutes by default.

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

## Download Issues

### "Refusing to write outside the download directory"

MCP downloads are confined to one directory: `~/Downloads/gemini-notebook` by
default, or `NOTEBOOKLM_DOWNLOAD_DIR` when the operator set it. The boundary
stops a download from landing on shell startup files, agent instruction files,
or git hooks, which matters because notebook source content is untrusted and
can carry instructions.

```python
# WRONG: absolute path outside the download directory
download_artifact(notebook_id="...", artifact_type="report", output_path="/Users/me/notes/report.md")

# CORRECT: relative to the download directory
download_artifact(notebook_id="...", artifact_type="report", output_path="report.md")
```

The response carries the absolute path the file was written to. Read the
destination from there rather than assuming it.

To save elsewhere, either move the file afterwards, run the `nlm` CLI (which
writes wherever the user points it), or have the operator set
`NOTEBOOKLM_DOWNLOAD_DIR` and restart the MCP server.

### "NotebookLM delivers AAC audio in an MP4 container"

Audio arrives as AAC inside MP4. Use a `.m4a` or `.mp4` suffix, not `.mp3`.
Transcode afterwards if MP3 is required:

```bash
nlm download audio <nb-id> --output raw.m4a
ffmpeg -i raw.m4a -acodec libmp3lame -q:a 2 podcast.mp3
```

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
