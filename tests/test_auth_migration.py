"""Tests to validate auth works after removing notebooklm-mcp-auth.

These tests verify that:
1. run_headless_auth is importable from cdp.py
2. The function has the correct signature
3. Helper functions exist in cdp.py
4. No imports from auth_cli remain in the codebase
"""

import pytest
from pathlib import Path


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
        )
        # All should be callable
        assert all(callable(f) for f in [
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
        ])


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


class TestMCPServerImports:
    """Test that MCP server still works with the new imports."""

    def test_mcp_server_imports(self):
        """MCP server should import without errors."""
        # This will fail if any imports are broken
        import notebooklm_tools.mcp.server

    def test_mcp_tools_import(self):
        """MCP tools should import without errors."""
        from notebooklm_tools.mcp.tools import refresh_auth, save_auth_tokens
        assert callable(refresh_auth)
        assert callable(save_auth_tokens)

    def test_client_imports(self):
        """Client modules should import without errors."""
        from notebooklm_tools.core.client import NotebookLMClient
        assert NotebookLMClient is not None
