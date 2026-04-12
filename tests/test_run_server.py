"""Tests for the desktop extension launcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

RUN_SERVER_PATH = Path(__file__).resolve().parents[1] / "desktop-extension" / "run_server.py"


def load_run_server_module():
    spec = importlib.util.spec_from_file_location("test_run_server_module", RUN_SERVER_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_find_uvx_checks_windows_install_locations(monkeypatch):
    module = load_run_server_module()
    expected = str(Path("/tmp/AppData/Local/uv/uvx.exe"))

    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(Path("/tmp/AppData/Local")))
    monkeypatch.setattr(
        module.os.path,
        "expanduser",
        lambda _value: str(Path("/tmp/home")),
    )
    monkeypatch.setattr(module.os.path, "isfile", lambda path: path == expected)
    monkeypatch.setattr(module.os, "access", lambda path, mode: path == expected)

    assert module._find_uvx() == expected


def test_launch_server_execs_in_place_on_non_windows(monkeypatch):
    module = load_run_server_module()
    seen = {}

    def fake_execvp(executable, argv):
        seen["executable"] = executable
        seen["argv"] = argv
        raise RuntimeError("stop after execvp")

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.os, "execvp", fake_execvp)

    with pytest.raises(RuntimeError, match="stop after execvp"):
        module._launch_server("/usr/local/bin/uvx", ["--transport", "stdio"])

    assert seen == {
        "executable": "/usr/local/bin/uvx",
        "argv": [
            "/usr/local/bin/uvx",
            "--from",
            "notebooklm-mcp-cli",
            "notebooklm-mcp",
            "--transport",
            "stdio",
        ],
    }


def test_launch_server_uses_subprocess_on_windows(monkeypatch):
    module = load_run_server_module()
    seen = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen["kwargs"] = kwargs
        return SimpleNamespace(returncode=23)

    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc_info:
        module._launch_server("C:/Users/test/AppData/Local/uv/uvx.exe", ["--transport", "stdio"])

    assert exc_info.value.code == 23
    assert seen["argv"] == [
        "C:/Users/test/AppData/Local/uv/uvx.exe",
        "--from",
        "notebooklm-mcp-cli",
        "notebooklm-mcp",
        "--transport",
        "stdio",
    ]
    assert seen["kwargs"] == {
        "stdin": module.sys.stdin,
        "stdout": module.sys.stdout,
        "stderr": module.sys.stderr,
        "check": False,
    }


def test_main_exits_with_helpful_error_when_uvx_missing(monkeypatch, capsys):
    module = load_run_server_module()

    monkeypatch.setattr(module, "_find_uvx", lambda: None)

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 1
    assert "Could not find 'uvx'" in capsys.readouterr().err
