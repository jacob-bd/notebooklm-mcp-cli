# Login Profile Mismatch Fix - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent `nlm login` from silently overwriting a profile's credentials with a different Google account.

**Architecture:** Add a guard inside `AuthManager.save_profile()` that compares the incoming email against the stored email and raises `AccountMismatchError` unless `force=True`. The CLI passes a `--force` flag through. Additionally, print the active profile name at login start and warn when connecting to a reused Chrome instance.

**Tech Stack:** Python 3.11+, Typer (CLI), pytest

---

### Task 1: Add `AccountMismatchError` Exception

**Files:**
- Modify: `src/notebooklm_tools/core/exceptions.py:100-107`
- Test: `tests/core/test_auth_guard.py` (create)

**Step 1: Write the failing test**

Create `tests/core/test_auth_guard.py`:

```python
"""Tests for account mismatch guard in profile saving."""

from notebooklm_tools.core.exceptions import AccountMismatchError, NLMError


def test_account_mismatch_error_inherits_nlm_error():
    """AccountMismatchError should be an NLMError."""
    assert issubclass(AccountMismatchError, NLMError)


def test_account_mismatch_error_contains_both_emails():
    """Error message should contain both the stored and new emails."""
    err = AccountMismatchError(
        stored_email="work@company.com",
        new_email="personal@gmail.com",
        profile_name="work",
    )
    assert "work@company.com" in str(err)
    assert "personal@gmail.com" in str(err)
    assert "work" in str(err)


def test_account_mismatch_error_has_hint():
    """Error should include a hint about --force."""
    err = AccountMismatchError(
        stored_email="work@company.com",
        new_email="personal@gmail.com",
        profile_name="work",
    )
    assert "--force" in err.hint
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_auth_guard.py -v`
Expected: FAIL with `ImportError: cannot import name 'AccountMismatchError'`

**Step 3: Write minimal implementation**

Add to `src/notebooklm_tools/core/exceptions.py` after `ProfileNotFoundError` (after line 107):

```python
class AccountMismatchError(NLMError):
    """Raised when trying to save credentials for a different account than what's stored."""

    def __init__(
        self,
        stored_email: str,
        new_email: str,
        profile_name: str,
    ) -> None:
        message = (
            f"Account mismatch for profile '{profile_name}': "
            f"stored account is '{stored_email}' but received credentials for '{new_email}'"
        )
        hint = "Use 'nlm login --force' to overwrite with the new account."
        super().__init__(message, hint)
        self.stored_email = stored_email
        self.new_email = new_email
        self.profile_name = profile_name
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_auth_guard.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add tests/core/test_auth_guard.py src/notebooklm_tools/core/exceptions.py
git commit -m "feat: add AccountMismatchError exception for profile protection"
```

---

### Task 2: Add Mismatch Guard to `save_profile()`

**Files:**
- Modify: `src/notebooklm_tools/core/auth.py:360-397`
- Test: `tests/core/test_auth_guard.py` (append)

**Step 1: Write the failing tests**

Append to `tests/core/test_auth_guard.py`:

```python
import json
import pytest
from pathlib import Path
from notebooklm_tools.core.auth import AuthManager
from notebooklm_tools.core.exceptions import AccountMismatchError


class TestSaveProfileMismatchGuard:
    """Tests for the account mismatch guard in save_profile()."""

    def _create_existing_profile(self, tmp_path: Path, email: str) -> AuthManager:
        """Helper: create a profile with existing credentials on disk."""
        profiles_dir = tmp_path / "profiles" / "test-profile"
        profiles_dir.mkdir(parents=True)

        cookies = [{"name": "SID", "value": "old-sid"}]
        (profiles_dir / "cookies.json").write_text(json.dumps(cookies))
        (profiles_dir / "metadata.json").write_text(json.dumps({
            "csrf_token": "old-token",
            "session_id": "old-session",
            "email": email,
            "last_validated": "2026-01-01T00:00:00",
        }))

        manager = AuthManager("test-profile")
        # Patch profile_dir to use tmp_path
        manager._test_profile_dir = profiles_dir
        return manager

    def test_save_blocks_when_email_differs(self, tmp_path, monkeypatch):
        """save_profile should raise AccountMismatchError when emails differ."""
        manager = self._create_existing_profile(tmp_path, "work@company.com")
        monkeypatch.setattr(
            "notebooklm_tools.utils.config.get_profile_dir",
            lambda name: tmp_path / "profiles" / name,
        )

        with pytest.raises(AccountMismatchError) as exc_info:
            manager.save_profile(
                cookies=[{"name": "SID", "value": "new-sid"}],
                email="personal@gmail.com",
            )
        assert "work@company.com" in str(exc_info.value)
        assert "personal@gmail.com" in str(exc_info.value)

    def test_save_allows_when_force_true(self, tmp_path, monkeypatch):
        """save_profile with force=True should overwrite even with different email."""
        manager = self._create_existing_profile(tmp_path, "work@company.com")
        monkeypatch.setattr(
            "notebooklm_tools.utils.config.get_profile_dir",
            lambda name: tmp_path / "profiles" / name,
        )

        profile = manager.save_profile(
            cookies=[{"name": "SID", "value": "new-sid"}],
            email="personal@gmail.com",
            force=True,
        )
        assert profile.email == "personal@gmail.com"

    def test_save_allows_when_emails_match(self, tmp_path, monkeypatch):
        """save_profile should work fine when emails match."""
        manager = self._create_existing_profile(tmp_path, "work@company.com")
        monkeypatch.setattr(
            "notebooklm_tools.utils.config.get_profile_dir",
            lambda name: tmp_path / "profiles" / name,
        )

        profile = manager.save_profile(
            cookies=[{"name": "SID", "value": "new-sid"}],
            email="work@company.com",
        )
        assert profile.email == "work@company.com"

    def test_save_allows_when_stored_email_is_none(self, tmp_path, monkeypatch):
        """save_profile should allow save when stored email is None (first-time setup)."""
        manager = self._create_existing_profile(tmp_path, None)
        monkeypatch.setattr(
            "notebooklm_tools.utils.config.get_profile_dir",
            lambda name: tmp_path / "profiles" / name,
        )

        profile = manager.save_profile(
            cookies=[{"name": "SID", "value": "new-sid"}],
            email="personal@gmail.com",
        )
        assert profile.email == "personal@gmail.com"

    def test_save_allows_when_new_email_is_none(self, tmp_path, monkeypatch):
        """save_profile should allow save when new email is None (extraction failed)."""
        manager = self._create_existing_profile(tmp_path, "work@company.com")
        monkeypatch.setattr(
            "notebooklm_tools.utils.config.get_profile_dir",
            lambda name: tmp_path / "profiles" / name,
        )

        profile = manager.save_profile(
            cookies=[{"name": "SID", "value": "new-sid"}],
            email=None,
        )
        # Should keep the old email when new is None
        assert profile is not None

    def test_save_allows_on_fresh_profile(self, tmp_path, monkeypatch):
        """save_profile should work on a brand new profile with no existing data."""
        profiles_dir = tmp_path / "profiles" / "new-profile"
        monkeypatch.setattr(
            "notebooklm_tools.utils.config.get_profile_dir",
            lambda name: profiles_dir,
        )

        manager = AuthManager("new-profile")
        profile = manager.save_profile(
            cookies=[{"name": "SID", "value": "first-sid"}],
            email="first@gmail.com",
        )
        assert profile.email == "first@gmail.com"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/core/test_auth_guard.py::TestSaveProfileMismatchGuard -v`
Expected: `test_save_blocks_when_email_differs` should FAIL (no guard exists yet, save succeeds without raising)

**Step 3: Write the implementation**

Modify `save_profile()` in `src/notebooklm_tools/core/auth.py`. Add `force` parameter and guard logic at the top of the method:

```python
def save_profile(
    self,
    cookies: list[dict] | dict[str, str],
    csrf_token: str | None = None,
    session_id: str | None = None,
    email: str | None = None,
    force: bool = False,
) -> Profile:
    """Save credentials to the current profile.

    Raises:
        AccountMismatchError: If the profile already has credentials for a
            different email and force is False.
    """
    from datetime import datetime
    from notebooklm_tools.core.exceptions import AccountMismatchError

    # Guard: check for account mismatch before overwriting
    if not force and email and self.metadata_file.exists():
        try:
            existing_metadata = json.loads(self.metadata_file.read_text())
            stored_email = existing_metadata.get("email")
            if stored_email and stored_email != email:
                raise AccountMismatchError(
                    stored_email=stored_email,
                    new_email=email,
                    profile_name=self.profile_name,
                )
        except (json.JSONDecodeError, KeyError):
            pass  # Corrupted metadata, allow overwrite

    self.profile_dir.mkdir(parents=True, exist_ok=True)
    # ... rest of method unchanged
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/core/test_auth_guard.py -v`
Expected: All PASSED

**Step 5: Run full test suite to check for regressions**

Run: `uv run pytest -v`
Expected: All existing tests still pass. Any callers of `save_profile()` that don't pass `force` will still work because the guard only fires when emails actually differ.

**Step 6: Commit**

```bash
git add src/notebooklm_tools/core/auth.py tests/core/test_auth_guard.py
git commit -m "feat: add account mismatch guard to save_profile()"
```

---

### Task 3: Add `--force` Flag and Profile Echo to CLI

**Files:**
- Modify: `src/notebooklm_tools/cli/main.py:82-280`

**Step 1: Add `--force` option to `login_callback()`**

Add after the `cdp_url` option (line ~108):

```python
force: bool = typer.Option(
    False, "--force",
    help="Force overwrite even if profile has credentials for a different account",
),
```

**Step 2: Add profile echo after profile resolution**

After line 131 (`auth = AuthManager(profile)`), add:

```python
# Show which profile is being authenticated
if not check and ctx.invoked_subcommand is None:
    try:
        existing = auth.load_profile()
        console.print(f"[dim]Authenticating profile: {profile} ({existing.email})[/dim]")
    except Exception:
        console.print(f"[dim]Authenticating profile: {profile}[/dim]")
```

**Step 3: Pass `force` to `save_profile()` calls**

Update the `auth.save_profile()` call (~line 255) to pass `force=force`:

```python
auth.save_profile(
    cookies=cookies,
    csrf_token=csrf_token,
    session_id=session_id,
    email=email,
    force=force,
)
```

**Step 4: Catch `AccountMismatchError` in the exception handler**

Add a catch block before the existing `NLMError` catch (~line 276):

```python
except AccountMismatchError as e:
    console.print(f"\n[red]Error:[/red] {e.message}")
    console.print(f"\n[yellow]Hint:[/yellow] {e.hint}")
    raise typer.Exit(1)
```

Import `AccountMismatchError` at the top of the try block alongside the other imports.

**Step 5: Run the full test suite**

Run: `uv run pytest -v`
Expected: All tests pass (CLI changes don't break existing behavior since `force` defaults to `False` and the guard only triggers on email mismatch)

**Step 6: Commit**

```bash
git add src/notebooklm_tools/cli/main.py
git commit -m "feat: add --force flag and profile echo to nlm login"
```

---

### Task 4: Add Reused Chrome Warning

**Files:**
- Modify: `src/notebooklm_tools/utils/cdp.py:509-516`
- Modify: `src/notebooklm_tools/cli/main.py` (after extraction result)

**Step 1: Add `reused_existing` flag to CDP return**

In `extract_cookies_via_cdp()`, track whether an existing Chrome was reused. After line 516 (`debugger_url = None`), set a flag:

```python
reused_existing = False

existing_port = find_existing_nlm_chrome()
if existing_port:
    port = existing_port
    debugger_url = get_debugger_url(port)
    reused_existing = True
else:
    debugger_url = None
```

Add `"reused_existing": reused_existing` to the return dict at line ~611.

**Step 2: Show warning in CLI when Chrome was reused**

In `login_callback()`, after `result = extract_cookies_via_cdp(...)` (~line 246), add:

```python
if result.get("reused_existing"):
    console.print(
        "[yellow]Warning:[/yellow] Connected to an already-running Chrome instance. "
        "Profile isolation may not apply — verify the account is correct."
    )
```

**Step 3: Run the full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/notebooklm_tools/utils/cdp.py src/notebooklm_tools/cli/main.py
git commit -m "feat: warn when connecting to reused Chrome instance during login"
```

---

### Task 5: Final Verification and Reinstall

**Step 1: Run full test suite one last time**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 2: Reinstall the package**

Run: `uv cache clean && uv tool install --force .`

**Step 3: Verify `--force` flag appears in help**

Run: `nlm login --help`
Expected: `--force` option is visible in the help output

**Step 4: Verify profile echo works**

Run: `nlm login --check`
Expected: Profile name and email shown in output

**Step 5: Commit any remaining changes and tag**

```bash
git status
# If clean, done. If anything remains, add and commit.
```
