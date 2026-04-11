"""Tests for supported authentication browser behavior."""

import json
from unittest.mock import patch


def test_select_auth_backend_ignores_firefox_preference_and_uses_chromium():
    from notebooklm_tools.utils.auth_browser import select_auth_backend

    with (
        patch("notebooklm_tools.utils.cdp._get_chromium_path", return_value="chromium"),
        patch("notebooklm_tools.utils.cdp.get_browser_display_name", return_value="Chromium"),
    ):
        backend = select_auth_backend("firefox")

    assert backend == {"backend": "chromium_cdp", "browser": "Chromium"}


def test_select_auth_backend_auto_prefers_chromium_when_available():
    from notebooklm_tools.utils.auth_browser import select_auth_backend

    with (
        patch("notebooklm_tools.utils.cdp._get_chromium_path", return_value="google-chrome"),
        patch("notebooklm_tools.utils.cdp.get_browser_display_name", return_value="Google Chrome"),
    ):
        backend = select_auth_backend("auto")

    assert backend == {"backend": "chromium_cdp", "browser": "Google Chrome"}


def test_select_auth_backend_returns_none_when_no_chromium_browser_available():
    from notebooklm_tools.utils.auth_browser import select_auth_backend

    with patch("notebooklm_tools.utils.cdp._get_chromium_path", return_value=None):
        backend = select_auth_backend("auto")

    assert backend is None


def test_supported_auth_browsers_excludes_firefox():
    from notebooklm_tools.utils.auth_browser import get_supported_auth_browsers

    with patch(
        "notebooklm_tools.utils.cdp.get_supported_browsers",
        return_value=["Google Chrome", "Chromium"],
    ):
        browsers = get_supported_auth_browsers()

    assert browsers == ["Google Chrome", "Chromium"]


def test_get_chromium_path_ignores_explicit_firefox_preference():
    from notebooklm_tools.utils.cdp import _get_chromium_path

    assert _get_chromium_path("firefox") is None


def test_saved_legacy_browser_backend_is_read_from_metadata(tmp_path, monkeypatch):
    from notebooklm_tools.core.auth import AuthManager
    from notebooklm_tools.utils.auth_browser import _get_saved_browser_backend

    monkeypatch.setenv("NOTEBOOKLM_MCP_CLI_PATH", str(tmp_path))

    auth = AuthManager("default")
    auth.save_profile(cookies={"SID": "sid", "HSID": "hsid"}, email="user@example.com")

    metadata = json.loads(auth.metadata_file.read_text(encoding="utf-8"))
    metadata["browser_backend"] = "firefox_playwright"
    auth.metadata_file.write_text(json.dumps(metadata), encoding="utf-8")

    assert _get_saved_browser_backend("default") == "firefox_playwright"
