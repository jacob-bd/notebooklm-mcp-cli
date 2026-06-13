# PR: Hardened ChatGPT artifact export links

## Summary

This branch adds an explicit, disabled-by-default outbound bridge for handing a NotebookLM artifact to ChatGPT through a short-lived, tokenized download route.

It is intentionally separate from ordinary `download_artifact` behavior. Nothing is staged unless the new outbound bridge tool is called directly and confirmed.

```text
NotebookLM artifact -> explicit staging -> tokenized route -> one-time/TTL-bound download
```

## New tools

```text
chatgpt_export_status
chatgpt_prepare_artifact_download
chatgpt_export_cleanup
```

## New route

```text
/chatgpt-exports/{token}
```

This is not the reverted broad `/artifacts/{filename}` route.

## Safety properties

- Disabled by default via `NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED`.
- Requires `NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL` before returning any external link.
- Requires `confirm=True` before staging an artifact.
- Uses high-entropy random tokens.
- Tokens expire by TTL.
- Tokens are one-time download by default.
- Multi-download links are explicit through `max_downloads`.
- Final download removes the token from the registry before serving the file.
- Final download schedules staged file deletion through a response background task.
- Expired tokens delete stale staged files on claim.
- Oversized staged files are rejected and deleted.
- Tool responses do not expose the local staged file path.
- Status responses do not expose the local cache path.

## Required configuration

```text
NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED=true
NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL=https://<your HTTPS tunnel origin>
```

Optional configuration:

```text
NOTEBOOKLM_CHATGPT_EXPORT_CACHE_DIR=<local staging directory>
NOTEBOOKLM_CHATGPT_EXPORT_TTL_SECONDS=600
NOTEBOOKLM_CHATGPT_EXPORT_MAX_BYTES=104857600
```

## What this avoids

This does not reintroduce the reverted bridge behavior:

- no broad public artifact directory;
- no filename-addressable `/artifacts/{filename}` route;
- no automatic `download_url` injection into ordinary tools;
- no automatic disk writes from `source_get_content`;
- no local file path disclosure in successful export tool responses.

## Validation performed

```text
ruff check: All checks passed
ruff format --check: clean
pytest tests/test_mcp_chatgpt_exports_hardened.py: 9 passed
pytest combined PR-specific suite: 38 passed locally
GitHub Actions: lint, tests, and version alignment passed
```

The tests cover:

- disabled-by-default behavior;
- required base URL;
- confirmation gate;
- successful tokenized staging;
- route-level expired-token 404;
- route-level one-time token invalidation;
- route-level multi-download countdown;
- oversized staged file rejection and deletion;
- no local path in successful tool response.

## Relationship to PR 229

PR 229 covers the inbound bridge:

```text
ChatGPT-hosted file -> NotebookLM file source
```

This branch covers the outbound bridge:

```text
NotebookLM artifact -> ChatGPT-downloadable short-lived token link
```

Reviewing these separately keeps the risk surfaces distinct.
