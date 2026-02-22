# Design: Fix `nlm login` Profile Account Mismatch

**Date:** 2026-02-21
**Status:** Approved
**Severity:** High

## Problem

`nlm login` can silently overwrite a profile's credentials with a different Google account's cookies. There is no validation, warning, or confirmation. This was discovered when the `work` profile was overwritten with personal account credentials after running `nlm login` while Chrome was logged into the personal Gmail.

### Root Causes

1. **No account mismatch guard in `save_profile()`** — credentials are written to disk without checking if the new email differs from the stored email
2. **No active profile echo at login start** — user has no indication which profile is being authenticated when `--profile` is omitted
3. **Existing Chrome bypasses profile isolation** — if Chrome is already running, CDP connects to it regardless of which profile's `user-data-dir` was requested

## Design

### Fix 1: Account Mismatch Guard in `AuthManager.save_profile()` (P0)

**File:** `src/notebooklm_tools/core/auth.py`

Add a `force` parameter to `save_profile()`. Before writing credentials:

1. Check if the profile already exists on disk
2. If it does, load the existing metadata and compare emails
3. If the new email differs from the stored email and `force=False`, raise `AccountMismatchError`
4. If `force=True`, proceed with the overwrite

This protects ALL callers — CLI, MCP, and any future code paths.

```python
# New exception in core/exceptions.py
class AccountMismatchError(NLMError):
    """Raised when trying to save credentials for a different account than what's stored."""
    pass
```

```python
# Updated save_profile signature
def save_profile(
    self,
    cookies: list[dict] | dict[str, str],
    csrf_token: str | None = None,
    session_id: str | None = None,
    email: str | None = None,
    force: bool = False,
) -> Profile:
```

Guard logic (before writing):
- If profile exists AND stored email is not None AND new email is not None AND they differ AND force is False → raise `AccountMismatchError`
- Skip the check if either email is None (first-time setup or email extraction failed)

### Fix 2: `--force` Flag in CLI `login_callback()` (P0)

**File:** `src/notebooklm_tools/cli/main.py`

- Add `--force` typer.Option to `login_callback()`
- Pass `force=force` to `auth.save_profile()`
- Catch `AccountMismatchError` and display a clear error message with both emails and instructions to use `--force`

### Fix 3: Print Active Profile at Login Start (P0)

**File:** `src/notebooklm_tools/cli/main.py`

After resolving the profile name (~line 131), print which profile is being authenticated:
```
Authenticating profile: work
```
If the profile already has a stored email:
```
Authenticating profile: work (kobystam@gmail.com)
```

### Fix 4: Warn When Connecting to Existing Chrome (P1)

**File:** `src/notebooklm_tools/utils/cdp.py`

In `extract_cookies_via_cdp()`, when `find_existing_nlm_chrome()` returns a port (line ~511), include `reused_existing=True` in the return dict.

**File:** `src/notebooklm_tools/cli/main.py`

After extraction, if `result.get("reused_existing")`, print:
```
Warning: Connected to an already-running Chrome instance.
Profile isolation may not apply — verify the account is correct.
```

This is informational only. The guard in Fix 1 is what actually prevents the wrong save.

## Files Changed

| File | Change |
|------|--------|
| `src/notebooklm_tools/core/exceptions.py` | Add `AccountMismatchError` |
| `src/notebooklm_tools/core/auth.py` | Add `force` param and mismatch guard to `save_profile()` |
| `src/notebooklm_tools/cli/main.py` | Add `--force` flag, catch mismatch error, print active profile, warn on reused Chrome |
| `src/notebooklm_tools/utils/cdp.py` | Add `reused_existing` flag to return dict |

## Not In Scope

- MCP server profile switching (separate feature)
- `refresh_auth` MCP tool profile parameter (separate feature)
- These are enhancements, not bugs, and don't cause data loss
