# PR: Hardened ChatGPT artifact export links

## Summary

This branch adds an explicit, disabled-by-default outbound bridge for handing a NotebookLM artifact to ChatGPT through a short-lived, tokenized download route.

It is intentionally separate from ordinary `download_artifact` behavior. Nothing is staged unless the new outbound bridge tool is called directly and confirmed.

```text
NotebookLM artifact -> explicit staging -> tokenized route -> one-time/TTL-bound download
```

## Issues addressed

This PR addresses the outbound side of the earlier bridge concerns without reintroducing the reverted broad artifact server:

- Public artifact exposure is addressed by using random, high-entropy, per-export tokens instead of filename-addressable routes.
- Long-lived link risk is addressed with TTL expiration and cleanup of expired staged files.
- Link reuse risk is addressed with one-time download by default and explicit `max_downloads` for the rare multi-download case.
- Local path disclosure is addressed by never returning the local staged file path in successful tool or status responses.
- Surprise serving behavior is addressed by requiring explicit export-tool invocation, `confirm=True`, and `NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED=true`.
- Tunnel exposure risk is addressed by requiring an explicit `NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL`; the server will not guess or silently expose a URL.

## New tools

```text
chatgpt_export_status
chatgpt_prepare_artifact_download
chatgpt_export_cleanup
```

## How to use with ChatGPT

This PR covers the outbound flow:

```text
NotebookLM artifact -> short-lived HTTPS link -> ChatGPT can fetch/download it
```

1. Expose the MCP server through a trusted HTTPS origin, such as a controlled Cloudflare Tunnel or equivalent reverse proxy.

2. Enable outbound exports in the MCP server environment:

   ```text
   NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED=true
   NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL=https://<your HTTPS tunnel origin>
   ```

3. In the MCP client, call:

   ```text
   chatgpt_export_status
   ```

   Confirm exports are enabled and the base URL is correct.

4. Generate or locate the NotebookLM artifact you want ChatGPT to read, then call:

   ```text
   chatgpt_prepare_artifact_download(
     notebook_id="<notebook-id>",
     artifact_id="<artifact-id>",
     confirm=true
   )
   ```

5. The tool stages the artifact and returns a short-lived URL like:

   ```text
   https://<your HTTPS tunnel origin>/chatgpt-exports/<token>
   ```

6. Paste that returned URL into ChatGPT or use it from ChatGPT while the token is still valid.

7. By default, the first successful download consumes the token and schedules the staged file for deletion. Use `max_downloads` only when multiple fetches are intentional.

8. Use `chatgpt_export_cleanup` to remove expired staged exports.

Important limitation: this does not create permanent public artifact links. The returned link is tokenized, TTL-bound, and one-time by default.

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
