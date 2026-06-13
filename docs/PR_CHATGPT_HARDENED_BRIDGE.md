# PR: Hardened ChatGPT file bridge

## Summary

This PR reintroduces ChatGPT-to-NotebookLM file handoff in a narrow, opt-in form after the reverted ChatGPT file bridge.

It intentionally keeps the earlier safe polling/auth branch as the base and adds only an explicit inbound bridge:

```text
trusted HTTPS file URL -> validated temporary download -> NotebookLM file source upload -> temp cleanup
```

It does not restore public artifact serving or add download links to ordinary MCP tool results.

## Why this is different from the reverted bridge

The reverted bridge had three review-blocking issues:

1. SSRF risk from accepting remote URLs without strict hostname/IP validation.
2. Disk leak risk from ordinary `source_get_content` calls writing files to disk.
3. Global behavior changes from injecting download URLs and file-serving behavior into existing tools.

This implementation addresses those by construction:

- the bridge is disabled by default;
- remote downloads require an explicit bridge tool call;
- a non-empty host allowlist is required;
- only `https://` URLs are accepted;
- hostnames are resolved and non-public addresses are rejected;
- redirects are manually followed and revalidated;
- file size and file extension allowlists are enforced;
- `confirm=True` is required before upload;
- temp files are deleted after upload by default;
- no `/artifacts` route is added;
- no `download_url` is added to `source_get_content` or `download_artifact`;
- ordinary read-only tools do not write files to disk.

## New tools

```text
chatgpt_bridge_status
chatgpt_add_file_source
chatgpt_bridge_cleanup
```

## Configuration

Required to enable the bridge:

```text
NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED=true
NOTEBOOKLM_CHATGPT_FILE_HOST_ALLOWLIST=host.example.com,*.trusted.example.com
```

Optional limits:

```text
NOTEBOOKLM_CHATGPT_FILE_MAX_BYTES=26214400
NOTEBOOKLM_CHATGPT_FILE_TTL_SECONDS=3600
NOTEBOOKLM_CHATGPT_FILE_CACHE_DIR=<custom cache directory>
```

## Validation performed

Static and unit validation:

```text
ruff: All checks passed
pytest: 27 passed
server import ok
```

Live NotebookLM validation:

```text
profile: pte
account: personaltouchelectronics@gmail.com
created disposable notebook: success
added trusted HTTPS test file as source: success
verified source_count: 1
cache cleanup: success
deleted disposable notebook: success
```

## Scope intentionally deferred

This PR only covers inbound ChatGPT file URL upload into NotebookLM.

The inverse flow is intentionally separate:

```text
NotebookLM artifact/source -> short-lived authenticated download link for ChatGPT
```

That outbound flow needs a separate design because it requires scoped file serving, tokens, TTLs, retention cleanup, and careful tunnel exposure controls.

## Files changed

```text
src/notebooklm_tools/mcp/tools/chatgpt_bridge.py
tests/test_mcp_chatgpt_bridge_hardened.py
src/notebooklm_tools/mcp/tools/__init__.py
src/notebooklm_tools/mcp/server.py
```
