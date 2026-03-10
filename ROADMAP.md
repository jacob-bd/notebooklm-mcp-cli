# ROADMAP

Canonical roadmap refreshed during the 2026-03-09 repo probe. Historical ideation
still lives in `WEEKEND_ROADMAP.md`, but this file is the prioritized backlog for
the next working sessions.

## Now

### 1. Prove PRD-NR01 nightly-refresh soak criteria
- Why it matters: the nightly runner is implemented, but the repo still lacks the
  evidence needed to close the remaining success criteria and trust unattended use.
- Evidence:
  - `10_docs/prds/PRD-NR01_nightly_notebook_refresh.md` shows status
    `Implemented ... pending soak validation`.
  - The unchecked success criteria are still:
    - zero orphaned duplicate sources after 3 consecutive nightly runs
    - zero orphaned duplicate sources after 3 consecutive nightly runs
  - The previous root roadmap already pointed to soak validation as the next milestone.
- Completed on 2026-03-10:
  - reviewed the 7-run nightly window in `refresh.log` and `sync_receipts/`
  - updated `PRD-NR01_nightly_notebook_refresh.md` with soak evidence
- Next concrete step: decide whether the remaining artifact timeout failures in
  other repos are acceptable for PRD closeout, or whether a second evidence
  window is needed before declaring soak complete.
- Effort: M
- Confidence: high
- Blockers / what lowers priority: expired NotebookLM auth, free-tier rate limits,
  or missing nightly receipts.

### 2. Add a read-only live smoke path for operator trust
- Why it matters: the local package looks healthy, but this repo's real risk lives
  in the live NotebookLM/auth contract, and that was not exercised during the probe.
- Evidence:
  - `Makefile` health is currently pytest-only.
  - `pyproject.toml` dev dependencies cover pytest/coverage but no separate smoke path.
  - `CLAUDE.md` and `META.yaml` both note cookie rotation / free-tier limits.
  - `docs/MCP_TEST_PLAN.md` contains a broad manual plan, but there is no short
    read-only runbook for routine operator confidence.
- Completed on 2026-03-10:
  - documented a read-only smoke ladder in `docs/CLI.md`,
    `docs/AUTHENTICATION.md`, `docs/TROUBLESHOOTING.md`, and
    `docs/NOTEBOOKLM_MCP_OPERATIONS_MANUAL.md`
- Next concrete step: decide whether that documented ladder should stay docs-only
  or be promoted into a lightweight `make smoke` wrapper.
- Effort: S
- Confidence: high
- Blockers / what lowers priority: requires valid auth and a stable known-good notebook.

## Next

### 3. Align auth guidance and reduce cookie-handling footguns
- Why it matters: the current auth story is workable, but the docs and templates
  still make it too easy to follow the wrong path or paste secrets into a tracked filename.
- Evidence:
  - `README.md` recommends auto mode first.
  - `docs/AUTHENTICATION.md` also recommends auto mode first.
  - `CLAUDE.md` emphasizes Chrome DevTools / cookie-first flows.
  - `uv run notebooklm-mcp-auth --help` currently describes file mode as recommended.
  - `cookies.txt` is a tracked template whose instructions explicitly tell the
    operator to paste real cookies into that filename.
  - `00_run/README.md` still says the directory is "Currently empty" even though
    install/uninstall scheduler scripts are present.
- Completed on 2026-03-10:
  - aligned operator docs and CLI help around auto mode as the preferred path
  - replaced the tracked `cookies.txt` template with `cookies.example.txt`
  - refreshed `00_run/README.md` to reflect the actual scheduler scripts
- Next concrete step: keep the docs-site/secondary docs in parity on future
  doc refreshes and watch for any auth guidance drift reappearing.
- Effort: S
- Confidence: high
- Blockers / what lowers priority: none beyond deciding the preferred onboarding path.

## Later

### 4. Decide whether the documented `src/` + `tests/` hybrid remains permanent
- Why it matters: the current layout is allowed, but the repo should either
  treat it as a stable packaging exception or eventually migrate to canonical
  C-series paths if C010 tightens enforcement.
- Evidence:
  - `rules_now.md` documents `src/` as the current legacy source layout.
  - `00_admin/audit_exceptions.yaml` explicitly allows `src` and `tests`.
  - `META.yaml` inventories the hybrid layout.
- First concrete step: record whether the exception is intended to remain long-term
  for Python packaging reasons, or whether a future migration should be scheduled.
- Effort: L
- Confidence: medium
- Blockers / what lowers priority: depends on future C010 policy and whether any
  enforcement actually changes.

## Completed Recently
- Standards alignment, repo contract repair, and roadmap/bootstrap cleanup landed
  on 2026-02-25.
- Deep audit alignment, primer refresh, and path-leak cleanup landed on 2026-02-26.
- Sync and operations docs were refreshed on 2026-03-05.

## Deferred / Not Worth It
- A wholesale `40_src/` / `60_tests/` migration is deferred for now.
  Reason: the repo already documents the `src/` / `tests/` hybrid in
  `rules_now.md`, `META.yaml`, and `00_admin/audit_exceptions.yaml`, so the move
  would be churn unless C010 policy or tooling starts requiring it.

## Decision Notes
- `ROADMAP.md` is now the canonical prioritized backlog.
- `WEEKEND_ROADMAP.md` remains a historical ideation artifact, not the active plan.
- `10_docs/prds/PRD-NR01_nightly_notebook_refresh.md` remains the implementation
  record for nightly refresh and should only be updated for PRD-status/evidence changes.
- `docs/BETTY_HANDOFF.md` remains useful background context, but not the source of
  record for next-session execution order.
