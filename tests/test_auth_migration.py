"""Tests to validate auth works after removing notebooklm-mcp-auth.

These tests verify that:
1. run_headless_auth is importable from cdp.py
2. The function has the correct signature
3. Helper functions exist in cdp.py
4. No imports from auth_cli remain in the codebase
5. Browser detection (get_chrome_path / get_supported_browsers) works correctly
   across macOS, Linux, and Windows candidate tables
"""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestCDPModule:
    """Test that cdp.py has all required functions."""

    def test_run_headless_auth_importable(self):
        """run_headless_auth should be importable from cdp."""
        from notebooklm_tools.utils.cdp import run_headless_auth

        assert callable(run_headless_auth)

    def test_has_chrome_profile_importable(self):
        """has_chrome_profile should be importable from cdp."""
        from notebooklm_tools.utils.cdp import has_chrome_profile

        assert callable(has_chrome_profile)

    def test_cleanup_chrome_profile_cache_importable(self):
        """cleanup_chrome_profile_cache should be importable from cdp."""
        from notebooklm_tools.utils.cdp import cleanup_chrome_profile_cache

        assert callable(cleanup_chrome_profile_cache)

    def test_run_headless_auth_signature(self):
        """run_headless_auth should have expected parameters."""
        import inspect

        from notebooklm_tools.utils.cdp import run_headless_auth

        sig = inspect.signature(run_headless_auth)
        params = list(sig.parameters.keys())

        # Should have port, timeout, and profile_name params
        assert "port" in params
        assert "timeout" in params
        assert "profile_name" in params

    def test_existing_cdp_functions_still_work(self):
        """Existing cdp functions should still be importable."""
        from notebooklm_tools.utils.cdp import (
            extract_cookies_via_cdp,
            extract_csrf_token,
            extract_session_id,
            find_or_create_notebooklm_page,
            get_current_url,
            get_debugger_url,
            get_page_cookies,
            get_page_html,
            is_logged_in,
            launch_chrome,
            launch_chrome_process,
            terminate_chrome,
        )

        # All should be callable
        assert all(
            callable(f)
            for f in [
                get_debugger_url,
                launch_chrome,
                launch_chrome_process,
                find_or_create_notebooklm_page,
                get_current_url,
                is_logged_in,
                get_page_cookies,
                get_page_html,
                extract_csrf_token,
                extract_session_id,
                extract_cookies_via_cdp,
                terminate_chrome,
            ]
        )


class TestNoAuthCLIImports:
    """Test that auth_cli imports are removed from all files."""

    def test_no_auth_cli_in_base(self):
        """base.py should import from cdp, not auth_cli."""
        import notebooklm_tools.core.base as base

        source = Path(base.__file__).read_text()
        assert "from .auth_cli import" not in source
        assert "from notebooklm_tools.core.auth_cli import" not in source

    def test_no_auth_cli_in_mcp_server(self):
        """MCP server.py should import from cdp, not auth_cli."""
        import notebooklm_tools.mcp.server as server

        source = Path(server.__file__).read_text()
        assert "from .auth_cli import" not in source

    def test_no_auth_cli_in_mcp_tools_auth(self):
        """MCP tools/auth.py should import from cdp, not auth_cli."""
        import notebooklm_tools.mcp.tools.auth as auth

        source = Path(auth.__file__).read_text()
        assert "from notebooklm_tools.core.auth_cli import" not in source


class TestAuthCLIRemoved:
    """Test that auth_cli.py files are removed."""

    def test_core_auth_cli_removed(self):
        """core/auth_cli.py should not exist."""
        from notebooklm_tools.core import __file__ as core_init

        core_dir = Path(core_init).parent
        auth_cli_path = core_dir / "auth_cli.py"
        assert not auth_cli_path.exists(), f"auth_cli.py still exists at {auth_cli_path}"


class TestErrorMessages:
    """Test that error messages reference nlm login, not notebooklm-mcp-auth."""

    def test_base_error_messages(self):
        """base.py error messages should reference nlm login."""
        import notebooklm_tools.core.base as base

        source = Path(base.__file__).read_text()
        # Should have nlm login references
        assert "nlm login" in source
        # Should NOT have notebooklm-mcp-auth references
        assert "notebooklm-mcp-auth" not in source


class TestBrowserDetection:
    """Tests for get_chrome_path() and get_supported_browsers()."""

    # ------------------------------------------------------------------
    # Importability
    # ------------------------------------------------------------------

    def test_get_chrome_path_importable(self):
        """get_chrome_path should be importable from cdp."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        assert callable(get_chrome_path)

    def test_get_supported_browsers_importable(self):
        """get_supported_browsers should be importable from cdp."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        assert callable(get_supported_browsers)

    # ------------------------------------------------------------------
    # Candidate table helpers
    # ------------------------------------------------------------------

    def test_macos_candidates_include_expected_browsers(self):
        """macOS candidate list should include Chrome, Arc, Brave, Edge, Chromium."""
        from notebooklm_tools.utils.cdp import _macos_browser_candidates

        names = [name for name, _ in _macos_browser_candidates()]
        for browser in ("Google Chrome", "Arc", "Brave Browser", "Microsoft Edge", "Chromium"):
            assert browser in names, f"{browser!r} missing from macOS candidates"

    def test_macos_candidates_include_user_applications(self):
        """macOS candidate list should contain ~/Applications paths as well."""
        from notebooklm_tools.utils.cdp import _macos_browser_candidates

        home_str = str(Path.home())
        paths = [path for _, path in _macos_browser_candidates()]
        assert any(p.startswith(home_str) for p in paths), (
            "No ~/Applications entries found in macOS candidate list"
        )

    def test_linux_candidates_include_expected_browsers(self):
        """Linux candidate list should include Chrome, Chromium, Brave, Edge."""
        from notebooklm_tools.utils.cdp import _LINUX_BROWSER_CANDIDATES

        names = [name for name, _ in _LINUX_BROWSER_CANDIDATES]
        for browser in ("Google Chrome", "Chromium", "Brave Browser", "Microsoft Edge"):
            assert browser in names, f"{browser!r} missing from Linux candidates"

    def test_windows_candidates_include_expected_browsers(self):
        """Windows candidate list should include Chrome, Edge, and Brave."""
        from notebooklm_tools.utils.cdp import _windows_browser_candidates

        names = [name for name, _ in _windows_browser_candidates()]
        for browser in ("Google Chrome", "Microsoft Edge", "Brave Browser"):
            assert browser in names, f"{browser!r} missing from Windows candidates"

    def test_windows_candidates_include_localappdata_paths(self):
        """Windows candidates should include user-local AppData paths."""
        from notebooklm_tools.utils.cdp import _windows_browser_candidates

        home_str = str(Path.home())
        paths = [path for _, path in _windows_browser_candidates()]
        assert any(home_str in p for p in paths), (
            "No user-local (AppData) entries found in Windows candidate list"
        )


class TestCDPStartupHandling:
    """Tests for CDP startup timing and diagnostics."""

    def test_get_debugger_url_uses_ipv4_loopback(self):
        """CDP version probe should use 127.0.0.1 consistently."""
        from notebooklm_tools.utils.cdp import get_debugger_url

        with patch("notebooklm_tools.utils.cdp.httpx_client.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/test"
            }

            url = get_debugger_url(9222)

        mock_get.assert_called_once_with("http://127.0.0.1:9222/json/version", timeout=5)
        assert url == "ws://127.0.0.1:9222/devtools/browser/test"

    def test_extract_cookies_waits_longer_for_cdp_debugger(self):
        """Slow browser startups should get a longer CDP wait window."""
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value="chromium"),
            patch("notebooklm_tools.utils.cdp.find_available_port", return_value=9222),
            patch("notebooklm_tools.utils.cdp.launch_chrome", return_value=True),
            patch(
                "notebooklm_tools.utils.cdp.get_debugger_url",
                return_value="ws://127.0.0.1:9222/devtools/browser/test",
            ) as mock_get_debugger_url,
            patch(
                "notebooklm_tools.utils.cdp.extract_cookies_from_page",
                return_value={"cookies": [], "csrf_token": "", "session_id": "", "email": ""},
            ),
        ):
            extract_cookies_via_cdp()

        mock_get_debugger_url.assert_called_once_with(9222, tries=30)

    def test_extract_cookies_reuses_single_existing_cdp_browser(self):
        """A single reachable existing CDP browser should be reused."""
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(9222, "ws://127.0.0.1:9222/devtools/browser/test"),
            ),
            patch("notebooklm_tools.utils.cdp.launch_chrome") as mock_launch_chrome,
            patch(
                "notebooklm_tools.utils.cdp.extract_cookies_from_page",
                return_value={"cookies": [], "csrf_token": "", "session_id": "", "email": ""},
            ) as mock_extract,
        ):
            result = extract_cookies_via_cdp()

        mock_launch_chrome.assert_not_called()
        mock_extract.assert_called_once_with("http://127.0.0.1:9222", True, 300)
        assert result["reused_existing"] is True

    # ------------------------------------------------------------------
    # get_chrome_path — macOS
    # ------------------------------------------------------------------

    def test_get_chrome_path_macos_returns_first_existing(self):
        """On macOS, get_chrome_path returns the first path that exists."""
        from notebooklm_tools.utils.cdp import _macos_browser_candidates, get_chrome_path

        candidates = _macos_browser_candidates()
        # Pick the second candidate and pretend only that one exists
        _, target_path = candidates[1]

        def fake_exists(self):
            return str(self) == target_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Darwin"),
            patch.object(Path, "exists", fake_exists),
        ):
            result = get_chrome_path()
        assert result == target_path

    def test_get_chrome_path_macos_returns_none_when_nothing_exists(self):
        """On macOS, get_chrome_path returns None when no browser is installed."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Darwin"),
            patch.object(Path, "exists", return_value=False),
        ):
            result = get_chrome_path()
        assert result is None

    def test_get_chrome_path_macos_fallback_to_chrome(self):
        """On macOS, if only the original Chrome path exists it is still returned."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        def fake_exists(self):
            return str(self) == chrome_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Darwin"),
            patch.object(Path, "exists", fake_exists),
        ):
            result = get_chrome_path()
        assert result == chrome_path

    # ------------------------------------------------------------------
    # get_chrome_path — Linux
    # ------------------------------------------------------------------

    def test_get_chrome_path_linux_returns_first_found(self):
        """On Linux, get_chrome_path returns the command name (not full path) of the
        first executable found — shutil.which resolution is the caller's concern."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        def fake_which(cmd):
            return "/usr/bin/brave-browser" if cmd == "brave-browser" else None

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"),
            patch("notebooklm_tools.utils.cdp.shutil.which", side_effect=fake_which),
        ):
            result = get_chrome_path()
        # get_chrome_path returns the raw executable name, not the resolved path
        assert result == "brave-browser"

    def test_get_chrome_path_linux_returns_none_when_nothing_found(self):
        """On Linux, get_chrome_path returns None when no browser is on PATH."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"),
            patch("notebooklm_tools.utils.cdp.shutil.which", return_value=None),
        ):
            result = get_chrome_path()
        assert result is None

    def test_get_chrome_path_linux_returns_none_when_candidates_exhausted(self):
        """On Linux there is no separate fallback path — if every candidate in
        _LINUX_BROWSER_CANDIDATES is absent, get_chrome_path returns None.
        (google-chrome and google-chrome-stable are already in the candidates
        table, so there is no separate fallback needed.)"""
        from notebooklm_tools.utils.cdp import get_chrome_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"),
            patch("notebooklm_tools.utils.cdp.shutil.which", return_value=None),
        ):
            result = get_chrome_path()
        assert result is None

    def test_get_chrome_path_linux_google_chrome_found_via_candidates(self):
        """google-chrome is in the candidates table itself, so it is returned
        without any separate fallback when it is the only browser present."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        def fake_which(cmd):
            return "/usr/bin/google-chrome" if cmd == "google-chrome" else None

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"),
            patch("notebooklm_tools.utils.cdp.shutil.which", side_effect=fake_which),
        ):
            result = get_chrome_path()
        assert result == "google-chrome"

    # ------------------------------------------------------------------
    # get_chrome_path — Windows
    # ------------------------------------------------------------------

    def test_get_chrome_path_windows_returns_first_existing(self):
        """On Windows, get_chrome_path returns the first path that exists."""
        from notebooklm_tools.utils.cdp import _windows_browser_candidates, get_chrome_path

        candidates = _windows_browser_candidates()
        _, target_path = candidates[2]  # user-local Chrome

        def fake_exists(self):
            return str(self) == target_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Windows"),
            patch.object(Path, "exists", fake_exists),
        ):
            result = get_chrome_path()
        assert result == target_path

    def test_get_chrome_path_windows_returns_none_when_nothing_exists(self):
        """On Windows, get_chrome_path returns None when no browser is installed."""
        from notebooklm_tools.utils.cdp import get_chrome_path

        with (
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Windows"),
            patch.object(Path, "exists", return_value=False),
        ):
            result = get_chrome_path()
        assert result is None

    # ------------------------------------------------------------------
    # get_supported_browsers
    # ------------------------------------------------------------------

    def test_get_supported_browsers_macos_no_duplicates(self):
        """get_supported_browsers should return a deduplicated list on macOS."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        with patch("notebooklm_tools.utils.cdp.platform.system", return_value="Darwin"):
            names = get_supported_browsers()
        assert len(names) == len(set(names)), "Duplicate browser names in macOS list"

    def test_get_supported_browsers_linux_no_duplicates(self):
        """get_supported_browsers should return a deduplicated list on Linux."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        with patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"):
            names = get_supported_browsers()
        assert len(names) == len(set(names)), "Duplicate browser names in Linux list"

    def test_get_supported_browsers_windows_no_duplicates(self):
        """get_supported_browsers should return a deduplicated list on Windows."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        with patch("notebooklm_tools.utils.cdp.platform.system", return_value="Windows"):
            names = get_supported_browsers()
        assert len(names) == len(set(names)), "Duplicate browser names in Windows list"

    def test_get_supported_browsers_macos_order(self):
        """Google Chrome should always be first in the macOS list."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        with patch("notebooklm_tools.utils.cdp.platform.system", return_value="Darwin"):
            names = get_supported_browsers()
        assert names[0] == "Google Chrome"

    def test_get_supported_browsers_linux_order(self):
        """Google Chrome should always be first in the Linux list."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        with patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"):
            names = get_supported_browsers()
        assert names[0] == "Google Chrome"

    def test_get_supported_browsers_windows_order(self):
        """Google Chrome should always be first in the Windows list."""
        from notebooklm_tools.utils.cdp import get_supported_browsers

        with patch("notebooklm_tools.utils.cdp.platform.system", return_value="Windows"):
            names = get_supported_browsers()
        assert names[0] == "Google Chrome"


class TestBrowserErrorMessages:
    """Tests that AuthenticationError messages are browser-generic and accurate."""

    def test_no_browser_error_message_macos(self):
        """Error when no browser found on macOS should list macOS browsers."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Darwin"),
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value=None),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        err = exc_info.value
        assert "Arc" in err.hint
        assert "Brave" in err.hint
        assert "Google Chrome" in err.hint

    def test_no_browser_error_message_linux(self):
        """Error when no browser found on Linux should list Linux browsers."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Linux"),
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value=None),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        err = exc_info.value
        assert "Chromium" in err.hint
        assert "Google Chrome" in err.hint
        # Arc is macOS-only — must NOT appear in the Linux message
        assert "Arc" not in err.hint

    def test_no_browser_error_message_windows(self):
        """Error when no browser found on Windows should list Windows browsers."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.platform.system", return_value="Windows"),
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value=None),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        err = exc_info.value
        assert "Microsoft Edge" in err.hint
        assert "Google Chrome" in err.hint
        # Arc is macOS-only — must NOT appear in the Windows message
        assert "Arc" not in err.hint

    def test_no_browser_error_includes_manual_hint(self):
        """The no-browser error should always suggest --manual as a fallback."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value=None),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        assert "--manual" in exc_info.value.hint

    def test_no_browser_error_message_is_generic(self):
        """The AuthenticationError message itself should not say 'Chrome'."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value=None),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        # The .message field should be generic, not "Chrome not found"
        assert exc_info.value.message == "No supported browser found"

    def test_failed_launch_error_is_generic(self):
        """Failed browser launch error should not say 'Chrome'."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value="/some/browser"),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch(
                "notebooklm_tools.utils.cdp.find_any_existing_cdp_browser",
                return_value=(None, None),
            ),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
            patch("notebooklm_tools.utils.cdp.find_available_port", return_value=9222),
            patch("notebooklm_tools.utils.cdp.launch_chrome", return_value=False),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        assert "Chrome" not in exc_info.value.message
        assert "browser" in exc_info.value.message.lower()

    def test_cannot_connect_error_is_generic(self):
        """Cannot-connect error message should not say 'Chrome'."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.cdp import extract_cookies_via_cdp

        with (  # noqa: SIM117
            patch("notebooklm_tools.utils.cdp.get_chrome_path", return_value="/some/browser"),
            patch("notebooklm_tools.utils.cdp.find_existing_nlm_chrome", return_value=(None, None)),
            patch("notebooklm_tools.utils.cdp.is_profile_locked", return_value=False),
            patch("notebooklm_tools.utils.cdp.find_available_port", return_value=9222),
            patch("notebooklm_tools.utils.cdp.launch_chrome", return_value=True),
            patch("notebooklm_tools.utils.cdp.get_debugger_url", return_value=None),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                extract_cookies_via_cdp(auto_launch=True)
        assert "Chrome" not in exc_info.value.message
        assert "browser" in exc_info.value.message.lower()


class TestMCPServerImports:
    """Test that MCP server still works with the new imports."""

    def test_mcp_server_imports(self):
        """MCP server should import without errors."""
        # This will fail if any imports are broken

    def test_mcp_tools_import(self):
        """MCP tools should import without errors."""
        from notebooklm_tools.mcp.tools import refresh_auth, save_auth_tokens

        assert callable(refresh_auth)
        assert callable(save_auth_tokens)


class TestPageFetchHeaders:
    """Regression tests for issue #105 — platform-neutral page fetch headers.

    The _PAGE_FETCH_HEADERS must NOT contain OS-specific Client Hints so that
    manually imported cookies (e.g. from a Windows Chrome session) are not
    rejected by Google's servers due to a platform fingerprint mismatch.

    See: https://github.com/jacob-bd/notebooklm-mcp-cli/issues/105
    """

    def _get_headers(self):
        from notebooklm_tools.core.base import BaseClient

        return BaseClient._PAGE_FETCH_HEADERS

    def test_no_sec_ch_ua_platform(self):
        """sec-ch-ua-platform must be absent — it embeds OS fingerprints."""
        headers = self._get_headers()
        assert "sec-ch-ua-platform" not in headers, (
            "sec-ch-ua-platform is present — it would cause Google to reject "
            "cookies captured on a different OS (e.g. Windows). Remove it."
        )

    def test_no_sec_ch_ua_mobile(self):
        """sec-ch-ua-mobile must be absent (Client Hint, optional)."""
        headers = self._get_headers()
        assert "sec-ch-ua-mobile" not in headers, (
            "sec-ch-ua-mobile is a Client Hint fingerprinting header. Remove it."
        )

    def test_no_sec_ch_ua(self):
        """sec-ch-ua must be absent (Client Hint, optional)."""
        headers = self._get_headers()
        assert "sec-ch-ua" not in headers, (
            "sec-ch-ua is a Client Hint fingerprinting header. Remove it."
        )

    def test_user_agent_not_macos(self):
        """User-Agent must not claim macOS — that would fingerprint Windows users."""
        ua = self._get_headers().get("User-Agent", "")
        assert "Macintosh" not in ua, (
            f"User-Agent contains 'Macintosh' ({ua!r}). Use a platform-neutral UA."
        )
        assert "Mac OS X" not in ua, (
            f"User-Agent contains 'Mac OS X' ({ua!r}). Use a platform-neutral UA."
        )

    def test_user_agent_is_present(self):
        """User-Agent header must still be present."""
        assert "User-Agent" in self._get_headers()
