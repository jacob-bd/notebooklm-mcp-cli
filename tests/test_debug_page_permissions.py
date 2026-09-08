"""Regression test for the debug_page.html dump permissions.

Covers GHSA-747w-q55c-m74m: the dump was written with the process umask and
chmod'd afterwards, leaving a window in which the authenticated page was
world-readable. It must be created 0o600 atomically instead.
"""

import os
import stat
import sys
from pathlib import Path

import httpx
import pytest

from notebooklm_tools.core import base


class _FakeResponse:
    url = "https://notebook.google.com/"
    status_code = 200
    text = "<html>no csrf token anywhere in here</html>"


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, *args, **kwargs):
        return _FakeResponse()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes only")
def test_debug_dump_is_created_private(tmp_path, monkeypatch):
    monkeypatch.setattr(httpx, "Client", _FakeClient)
    monkeypatch.setattr(base.BaseClient, "_get_httpx_cookies", lambda self: {})
    monkeypatch.setattr(
        "notebooklm_tools.core.cookie_rotation.rotate_google_cookies", lambda c: None
    )
    monkeypatch.setattr("notebooklm_tools.utils.config.get_storage_dir", lambda: tmp_path)

    client = base.BaseClient.__new__(base.BaseClient)
    monkeypatch.setattr(type(client), "_get_base_url", lambda self: "https://notebook.google.com")
    monkeypatch.setattr(type(client), "_is_enterprise", lambda self: False)

    # The file must be private at creation, not narrowed afterwards. A
    # post-hoc chmod leaves a window, and this codebase suppressed its
    # OSError, so a failed chmod left the dump world-readable forever.
    # Patching chmod to fail proves the mode does not depend on it.
    def _refuse_chmod(self, mode):
        raise OSError("chmod refused")

    monkeypatch.setattr(Path, "chmod", _refuse_chmod)

    # A loose umask must not widen the file either.
    old_umask = os.umask(0o000)
    try:
        with pytest.raises(ValueError, match="Could not extract CSRF token"):
            client._refresh_auth_tokens()
    finally:
        os.umask(old_umask)

    debug_file = tmp_path / "debug_page.html"
    assert debug_file.exists(), "debug dump should have been written"
    mode = stat.S_IMODE(debug_file.stat().st_mode)
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"
    assert debug_file.read_text() == _FakeResponse.text
