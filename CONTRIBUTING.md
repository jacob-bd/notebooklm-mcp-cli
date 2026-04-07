# Contributing

## Prerequisites

- Python 3.11+
- `uv` (`brew install uv` or `pip install uv`)
- `gcloud` SDK for enterprise testing (`brew install google-cloud-sdk`)
- A Google account

## Dev environment setup

```bash
git clone https://github.com/Robiton/notebooklm-mcp-cli.git
cd notebooklm-mcp-cli
uv sync --all-extras
uv run pytest -m "not e2e"   # should pass
uvx ruff check .              # should be clean
```

## Issue routing

Personal mode bugs should go to `jacob-bd/notebooklm-mcp-cli` first. Enterprise mode bugs should be filed here.

This fork adds enterprise support on top of upstream personal features, so personal-only regressions often belong upstream while enterprise-specific behavior is owned here.

## PR process

- Use branch names in the form `feat/*`, `fix/*`, or `chore/*`.
- Load `ai/STANDARDS.md` before starting work.
- Use the pull request template checklist.
- Commits co-authored with Claude or Codex must still pass the required tests and checks.

## Testing requirements

- Do not include e2e tests in PRs; they require live authentication.
- Mock at the `NotebookLMClient` level.
- Mark enterprise e2e coverage with `@pytest.mark.e2e`.

## Enterprise testing notes

Enterprise testing requires:

- A GCP project with the Discovery Engine API enabled
- `gcloud auth application-default login`
- `NOTEBOOKLM_PROJECT_ID` set in the environment

## Architecture

`cli/` and `mcp/` are thin wrappers. `services/` contains business logic. `core/` contains raw API calls.

Do not add `if-is-enterprise` branches in `services/`; use the adapter pattern instead.

## What not to submit

- Upstream-only features; send those to `jacob-bd/notebooklm-mcp-cli`
- Breaking changes to personal mode without enterprise parity
- Credentials, tokens, or other secrets

## Upstream sync procedure

Briefly review upstream changes with `git fetch upstream && git log HEAD..upstream/main`.

Known conflict hotspots:

- `mcp/server.py`
- `core/__init__.py`
- `utils/config.py`
- `pyproject.toml`
- `CHANGELOG.md`
