# Safe polling and auth-health changes

This note documents the hardened subset intentionally kept after reverting the ChatGPT file bridge.

## Included

- `source_get_content` now accepts `wait`, `wait_timeout`, and `poll_interval`.
- `download_artifact` now accepts `wait`, `wait_timeout`, and `poll_interval`.
- `studio_create` uses the shared `AuthHealthChecker` path introduced by the multi-probe auth-health work.
- Headless Chrome profile detection recognizes both legacy and modern cookie database locations:
  - `Default/Cookies`
  - `Default/Network/Cookies`

## Intentionally excluded

The ChatGPT file upload/download bridge is not included in this branch.

Specifically, this branch does not add:

- a public `/artifacts/{filename}` route;
- automatic disk writes from read-only tools such as `source_get_content`;
- automatic `download_url` fields in ordinary MCP tool results;
- broad remote URL downloading from ChatGPT file references.

Those behaviors require a hardened design with explicit opt-in, strict host allowlisting, bounded retention/cleanup, and no behavioral changes for non-ChatGPT users.
