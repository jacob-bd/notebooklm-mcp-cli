# Receipt: Deep Review Modernization + Hardening

**Date:** 2026-02-25  
**Repo:** C021_notebooklm-mcp  
**PRD:** OPTIONAL (maintenance hardening; no product-scope PRD required)

## What Changed

1. Hardened sync update safety to prevent source loss:
   - `sync_cli.sync_files()` now adds replacement source first, then best-effort deletes old source.
   - `doc_refresh.notebook_sync.apply_sync_plan()` now follows add-first replacement logic and records warnings on cleanup failure.

2. Fixed artifact completion polling correctness:
   - `doc_refresh.artifact_refresh.apply_artifact_plan()` now tracks exact created `artifact_id` values.
   - Polling now completes only when those specific IDs reach terminal status.

3. Implemented major-version trigger behavior:
   - `doc_refresh.runner._detect_major_version_bump()` now compares stored `meta_version` with current `META.yaml` version.
   - `doc_refresh.runner._update_notebook_map()` now persists current `meta_version` during sync updates.

4. Moved mutable doc-refresh state handling to config path:
   - `doc_refresh.manifest.DEFAULT_NOTEBOOK_MAP_PATH` now defaults to `~/.config/notebooklm-mcp/notebook_map.yaml`.
   - Added `save_notebook_map()` helper.
   - Added packaged `notebook_map.template.yaml` bootstrap.
   - Removed bundled mutable runtime files from package source (`notebook_map.yaml` + `sync_receipts/*.json`).

5. Improved auth cookie parsing robustness:
   - `server.save_auth_tokens()` now parses cookie headers with either `"; "` or `";"` separators.

6. Modernized quality gates and entrypoints:
   - Added CI workflow at `.github/workflows/ci.yml` (tests + coverage report + build).
   - Added `doc-refresh` console script entrypoint in `pyproject.toml`.
   - Added `pytest-cov` dev dependency.

7. Updated docs + changelog:
   - Security/privacy docs now reflect persisted local doc-refresh state.
   - Code tour and doc-refresh phase docs updated for notebook map template/runtime path model.
   - `CHANGELOG.md` updated under `[Unreleased]`.

8. Added regression tests:
   - Sync safety ordering and cleanup warning behavior.
   - Artifact completion ID matching behavior.
   - Major-version detection using stored `meta_version`.
   - Cookie parsing without spaces after semicolons.

## Why

The repository review identified correctness and operational risks:
- possible source loss on replacement sync failures,
- false-positive artifact completion,
- inert major-version trigger logic,
- mutable state embedded in distributable package,
- brittle cookie parsing,
- and weak CI coverage gates.

This patch set addresses those highest-risk findings first while keeping existing user-facing MCP tool semantics stable.

## Verification Evidence

Executed in repo root:

```bash
git pull --ff-only
uv run pytest -q
uv run pytest --cov=notebooklm_mcp --cov-report=term-missing -q
uv run python -m compileall -q src tests
uv build
uv run python - <<'PY'
import zipfile
whl='dist/notebooklm_mcp_server-0.1.0-py3-none-any.whl'
with zipfile.ZipFile(whl) as z:
    names=sorted(z.namelist())
for n in names:
    if 'doc_refresh/' in n:
        print(n)
PY
```

Observed:
- `pytest -q`: **36 passed**
- coverage run: **36 passed**, total coverage reported **20%** (improved from prior baseline)
- compileall: no syntax errors
- build: wheel + sdist built successfully
- wheel contents: includes `notebook_map.template.yaml`; excludes prior `sync_receipts/*.json` and mutable `notebook_map.yaml`

## Files Touched

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `CHANGELOG.md`
- `src/notebooklm_mcp/server.py`
- `src/notebooklm_mcp/sync_cli.py`
- `src/notebooklm_mcp/doc_refresh/manifest.py`
- `src/notebooklm_mcp/doc_refresh/__init__.py`
- `src/notebooklm_mcp/doc_refresh/runner.py`
- `src/notebooklm_mcp/doc_refresh/notebook_sync.py`
- `src/notebooklm_mcp/doc_refresh/artifact_refresh.py`
- `src/notebooklm_mcp/doc_refresh/notebook_map.template.yaml`
- `tests/test_doc_refresh.py`
- `tests/test_server_tools.py`
- `docs/notebooklm_mcp/SECURITY_AND_PRIVACY.md`
- `docs/notebooklm_mcp/CODE_TOUR.md`
- `docs/doc_refresh/PHASE_1_FOUNDATION.md`
- `docs/BETTY_HANDOFF.md`

Removed:
- `src/notebooklm_mcp/doc_refresh/notebook_map.yaml`
- `src/notebooklm_mcp/doc_refresh/sync_receipts/*.json`
