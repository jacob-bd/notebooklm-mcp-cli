# Coding Standards

## General

- Write code for the next person to read, not just the next run
- One function, one responsibility
- No commented-out dead code in commits
- Prefer clarity over cleverness
- Files over 300 lines should be split into smaller modules

## Naming conventions

| Context | Style | Example |
|---------|-------|---------|
| Files | snake_case | enterprise_client.py |
| Python variables and functions | snake_case | get_user_token() |
| Constants | UPPER_SNAKE_CASE | MAX_RETRY_COUNT |
| Classes | PascalCase | EnterpriseClient |
| TypedDicts | PascalCase | AddSourceResult |

## Documentation

- Every function gets a docstring
- Document the why, not just the what
- README stays current with every major change
- Inline comments only when logic is non-obvious

## Version control

Commit message format: `type(scope): description`

```
feat(enterprise): add audio overview support
fix(sources): correct paywall check SSRF vulnerability
docs(auth): add enterprise authentication section
chore(deps): update uv.lock
refactor(client): remove dead enterprise batchexecute code paths
test(sources): update bulk add tests for per-URL processing
```

| Type | Use for |
|------|---------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Build, deps, tooling — no logic change |
| `refactor` | Code restructure — no behavior change |
| `test` | Adding or updating tests |
| `style` | Formatting only — no logic change |

## Project-specific layering rules

```
cli/ and mcp/     →  thin wrappers only (UX, JSON responses)
services/         →  all business logic, validation, error handling
core/             →  low-level API calls only (no business logic)
utils/            →  config, auth, CDP, browser helpers
```

- `cli/` and `mcp/` must NOT import from `core/` directly — always go through `services/`
- `services/` raises `ServiceError`/`ValidationError` — never raw exceptions
- `core/` returns raw dicts from API calls — no business logic
- Enterprise and personal mode are selected at the `mcp/tools/_utils.get_client()` call site

## Testing

- `uv run pytest` — run full suite
- Tests must pass with `NOTEBOOKLM_MODE=personal` (set by `tests/conftest.py` autouse fixture)
- Do not use live API calls in tests — mock at the client layer
- Lint: `uvx ruff check .` and `uvx ruff format --check .` must be clean before pushing

## Dependencies

- Pin dependency versions in `uv.lock`
- Run `uvx pip-audit` before each release
- `httpx` for HTTP in enterprise/podcast clients; `requests` is used by the personal client
- Never add a new dependency without checking license and maintenance status

---

# API Integration Overlay — Coding Standards

_Extends base coding standards for API integration work in this project._

## Client structure

Each API surface has its own client class:

- `core/client.py` — personal batchexecute client (auth, request, retry)
- `core/enterprise_client.py` — enterprise Discovery Engine REST client
- `core/enterprise_adapter.py` — adapts enterprise client to personal client interface

Business logic lives in `services/`, not in the client classes.

## Retry and rate limit handling

```python
# Enterprise client uses httpx with explicit timeout
response = self._client.request("POST", url, headers=self._headers(), json=body, timeout=30)
```

- Retryable: 429, 500, 502, 503, 504
- Non-retryable: 400, 401, 403, 404 — fail immediately with clear error
- Enterprise 401: prompt `gcloud auth login`
- Enterprise 403: prompt IAM role assignment

## Error message hygiene

```python
# Strip auth headers from exception messages — never expose tokens
except httpx.HTTPStatusError as e:
    raise httpx.HTTPStatusError(
        f"API error: {e.response.status_code}",  # No headers, no body
        request=e.request,
        response=e.response,
    ) from None
```

## Mocking in tests

```python
# tests/conftest.py forces personal mode for all tests
@pytest.fixture(autouse=True)
def force_personal_mode(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_MODE", "personal")
    reset_config()
    yield
    reset_config()
```

Never make live API calls in tests. Mock at the `NotebookLMClient` method level.

## What not to do

- Never use `shell=True` in subprocess calls (command injection risk)
- Never log full request or response bodies — they may contain cookies or tokens
- Never retry 4xx errors — they indicate a request problem, not a server problem
- Never store API responses to disk without confirming they contain no credentials
- Never hardcode base URLs — use `get_base_url()` from `utils/config.py`
- Never add `if is_enterprise:` branches inside service or core layers — use the adapter pattern
