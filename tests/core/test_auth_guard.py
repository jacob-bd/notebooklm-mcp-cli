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
