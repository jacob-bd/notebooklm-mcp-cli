"""Tests for the `nlm auth refresh` command (issue #316, suggestion #3)."""

from types import SimpleNamespace

from typer.testing import CliRunner

from notebooklm_tools.cli.main import app


def test_auth_refresh_success(monkeypatch):
    """A successful headless refresh reports success and exits 0."""
    calls: list[str] = []

    def fake_headless(*, profile_name, timeout=30):
        calls.append(profile_name)
        return SimpleNamespace(cookies={"SID": "fresh"})

    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)
    monkeypatch.setattr("notebooklm_tools.utils.auth_browser.run_headless_auth", fake_headless)

    result = CliRunner().invoke(app, ["auth", "refresh", "--profile", "work"])

    assert result.exit_code == 0
    assert calls == ["work"]
    assert "refreshed" in result.output.lower()


def test_auth_refresh_uses_default_profile(monkeypatch):
    """Without --profile, the configured default profile is refreshed."""
    calls: list[str] = []

    def fake_headless(*, profile_name, timeout=30):
        calls.append(profile_name)
        return SimpleNamespace(cookies={"SID": "fresh"})

    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)
    monkeypatch.setattr(
        "notebooklm_tools.utils.config.get_config",
        lambda: SimpleNamespace(auth=SimpleNamespace(default_profile="acct")),
    )
    monkeypatch.setattr("notebooklm_tools.utils.auth_browser.run_headless_auth", fake_headless)

    result = CliRunner().invoke(app, ["auth", "refresh"])

    assert result.exit_code == 0
    assert calls == ["acct"]


def test_auth_refresh_failure_exits_nonzero(monkeypatch):
    """When headless refresh cannot recover, exit non-zero for schedulers."""
    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)
    monkeypatch.setattr(
        "notebooklm_tools.utils.auth_browser.run_headless_auth",
        lambda *, profile_name, timeout=30: None,
    )

    result = CliRunner().invoke(app, ["auth", "refresh", "--profile", "work"])

    assert result.exit_code == 1
    assert "could not refresh" in result.output.lower()


def test_auth_refresh_blocks_when_env_cookies_override(monkeypatch):
    """NOTEBOOKLM_COOKIES overrides disk auth, so refresh is refused up front."""
    called = False

    def fake_headless(*, profile_name, timeout=30):
        nonlocal called
        called = True
        return SimpleNamespace(cookies={"SID": "fresh"})

    monkeypatch.setenv("NOTEBOOKLM_COOKIES", "SID=abc")
    monkeypatch.setattr("notebooklm_tools.utils.auth_browser.run_headless_auth", fake_headless)

    result = CliRunner().invoke(app, ["auth", "refresh"])

    assert result.exit_code == 1
    assert "NOTEBOOKLM_COOKIES" in result.output
    assert called is False
