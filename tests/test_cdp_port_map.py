"""Regression tests for CDP port-map profile isolation (Issue #244)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from notebooklm_tools.utils import cdp


@pytest.fixture
def storage_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("notebooklm_tools.utils.config.get_storage_dir", lambda: tmp_path)
    # Keep port-map PIDs alive during tests (pytest PIDs are synthetic).
    monkeypatch.setattr("os.kill", lambda pid, sig: None)
    return tmp_path


def _write_port_map(storage_dir: Path, data: dict) -> None:
    map_file = storage_dir / "chrome-port-map.json"
    map_file.write_text(json.dumps(data), encoding="utf-8")


def test_find_existing_nlm_chrome_reuses_only_matching_profile(storage_dir):
    _write_port_map(
        storage_dir,
        {
            "9222": {"profile": "work", "pid": 111},
            "9223": {"profile": "default", "pid": 222},
        },
    )
    version = {
        "webSocketDebuggerUrl": "ws://127.0.0.1:9223/devtools/browser/abc",
        "User-Agent": "Mozilla/5.0 Chrome/124",
    }

    with (
        patch.object(cdp, "_fetch_cdp_version", return_value=version),
        patch.object(cdp, "_mapped_chrome_owns_profile", return_value=True),
    ):
        port, url = cdp.find_existing_nlm_chrome(profile_name="default")

    assert port == 9223
    assert url == "ws://127.0.0.1:9223/devtools/browser/abc"


def test_find_existing_nlm_chrome_ignores_foreign_profile_entries(storage_dir):
    _write_port_map(storage_dir, {"9222": {"profile": "work", "pid": 111}})

    with patch.object(cdp, "_fetch_cdp_version") as mock_fetch:
        port, url = cdp.find_existing_nlm_chrome(profile_name="default")

    assert (port, url) == (None, None)
    mock_fetch.assert_not_called()


def test_find_existing_nlm_chrome_clears_stale_unresponsive_port(storage_dir):
    _write_port_map(storage_dir, {"9222": {"profile": "default", "pid": 111}})

    with patch.object(cdp, "_fetch_cdp_version", return_value=None):
        port, url = cdp.find_existing_nlm_chrome(profile_name="default")

    assert (port, url) == (None, None)
    assert json.loads((storage_dir / "chrome-port-map.json").read_text(encoding="utf-8")) == {}


def test_find_existing_nlm_chrome_skips_headless_mapped_browser(storage_dir):
    _write_port_map(storage_dir, {"9222": {"profile": "default", "pid": 111}})
    version = {
        "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc",
        "User-Agent": "Mozilla/5.0 HeadlessChrome/124",
    }

    with patch.object(cdp, "_fetch_cdp_version", return_value=version):
        port, url = cdp.find_existing_nlm_chrome(profile_name="default")

    assert (port, url) == (None, None)
    assert json.loads((storage_dir / "chrome-port-map.json").read_text(encoding="utf-8")) == {}


def test_find_existing_nlm_chrome_clears_port_when_pid_uses_foreign_profile(storage_dir):
    _write_port_map(storage_dir, {"9222": {"profile": "default", "pid": 999}})
    version = {
        "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc",
        "User-Agent": "Mozilla/5.0 Chrome/124",
    }
    profile_dir = storage_dir / "nlm-profile"
    profile_dir.mkdir()
    foreign_cmdline = (
        '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '
        '--remote-debugging-port=9222 --user-data-dir="C:\\agent-browser-profile"'
    )

    with (
        patch.object(cdp, "_fetch_cdp_version", return_value=version),
        patch.object(cdp, "_get_profile_dir_for_launch", return_value=profile_dir),
        patch.object(cdp, "get_chrome_path", return_value="chrome.exe"),
        patch.object(cdp, "_get_process_cmdline", return_value=foreign_cmdline),
    ):
        port, url = cdp.find_existing_nlm_chrome(profile_name="default")

    assert (port, url) == (None, None)
    assert json.loads((storage_dir / "chrome-port-map.json").read_text(encoding="utf-8")) == {}


def test_mapped_chrome_owns_profile_matches_user_data_dir_flag(tmp_path, monkeypatch):
    profile_dir = tmp_path / "chrome-profile"
    profile_dir.mkdir()
    monkeypatch.setattr(
        cdp,
        "_get_profile_dir_for_launch",
        lambda _chrome_path, _profile_name: profile_dir,
    )
    monkeypatch.setattr(cdp, "get_chrome_path", lambda: "/usr/bin/google-chrome")

    cmdline = f"/usr/bin/google-chrome --remote-debugging-port=9222 --user-data-dir={profile_dir}"
    with patch.object(cdp, "_get_process_cmdline", return_value=cmdline):
        assert cdp._mapped_chrome_owns_profile(1234, "default", 9222) is True


def test_mapped_chrome_owns_profile_matches_quoted_windows_path(tmp_path, monkeypatch):
    profile_dir = tmp_path / "John Doe" / "nlm-profile"
    profile_dir.mkdir(parents=True)
    monkeypatch.setattr(
        cdp,
        "_get_profile_dir_for_launch",
        lambda _chrome_path, _profile_name: profile_dir,
    )
    monkeypatch.setattr(cdp, "get_chrome_path", lambda: "chrome.exe")

    win_path = str(profile_dir).replace("/", "\\")
    cmdline = (
        f'"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '
        f'--remote-debugging-port=9222 --user-data-dir="{win_path}"'
    )
    with patch.object(cdp, "_get_process_cmdline", return_value=cmdline):
        assert cdp._mapped_chrome_owns_profile(1234, "default", 9222) is True


def test_mapped_chrome_owns_profile_rejects_foreign_user_data_dir(tmp_path, monkeypatch):
    profile_dir = tmp_path / "nlm-profile"
    profile_dir.mkdir()
    monkeypatch.setattr(
        cdp,
        "_get_profile_dir_for_launch",
        lambda _chrome_path, _profile_name: profile_dir,
    )
    monkeypatch.setattr(cdp, "get_chrome_path", lambda: "/usr/bin/google-chrome")

    cmdline = (
        "/usr/bin/google-chrome --remote-debugging-port=9222 "
        "--user-data-dir=/tmp/agent-browser-profile"
    )
    with patch.object(cdp, "_get_process_cmdline", return_value=cmdline):
        assert cdp._mapped_chrome_owns_profile(1234, "default", 9222) is False


def test_mapped_chrome_owns_profile_fails_closed_when_cmdline_unavailable(tmp_path, monkeypatch):
    profile_dir = tmp_path / "nlm-profile"
    profile_dir.mkdir()
    monkeypatch.setattr(
        cdp,
        "_get_profile_dir_for_launch",
        lambda _chrome_path, _profile_name: profile_dir,
    )
    monkeypatch.setattr(cdp, "get_chrome_path", lambda: "/usr/bin/google-chrome")

    with patch.object(cdp, "_get_process_cmdline", return_value=None):
        assert cdp._mapped_chrome_owns_profile(1234, "default", 9222) is False


def test_mapped_chrome_owns_profile_rejects_pid_on_wrong_debug_port(tmp_path, monkeypatch):
    profile_dir = tmp_path / "nlm-profile"
    profile_dir.mkdir()
    monkeypatch.setattr(
        cdp,
        "_get_profile_dir_for_launch",
        lambda _chrome_path, _profile_name: profile_dir,
    )
    monkeypatch.setattr(cdp, "get_chrome_path", lambda: "/usr/bin/google-chrome")

    cmdline = f"/usr/bin/google-chrome --remote-debugging-port=9223 --user-data-dir={profile_dir}"
    with patch.object(cdp, "_get_process_cmdline", return_value=cmdline):
        assert cdp._mapped_chrome_owns_profile(1234, "default", 9222) is False


@pytest.mark.skipif(not Path(f"/proc/{os.getpid()}/cmdline").exists(), reason="Linux /proc only")
def test_get_process_cmdline_reads_linux_proc():
    cmdline = cdp._get_process_cmdline(os.getpid())
    assert cmdline is not None
    assert "python" in cmdline.lower()
