"""Targeted tests for server tool behaviors."""

import sys
import types
from pathlib import Path

from notebooklm_mcp import auth as auth_module


class _FakeFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self):
        def decorator(fn):
            return fn

        return decorator


fake_fastmcp = types.ModuleType("fastmcp")
fake_fastmcp.FastMCP = _FakeFastMCP
sys.modules.setdefault("fastmcp", fake_fastmcp)

from notebooklm_mcp import server


def test_save_auth_tokens_parses_cookie_header_without_spaces(monkeypatch, tmp_path: Path):
    """save_auth_tokens should accept cookie strings with or without '; ' spacing."""
    captured = {}

    def fake_save(tokens, silent: bool = False):
        captured["tokens"] = tokens

    monkeypatch.setattr(auth_module, "save_tokens_to_cache", fake_save)
    monkeypatch.setattr(auth_module, "get_cache_path", lambda: tmp_path / "auth.json")

    result = server.save_auth_tokens(
        cookies="SID=a;HSID=b;SSID=c;APISID=d;SAPISID=e"
    )

    assert result["status"] == "success"
    tokens = captured["tokens"]
    assert tokens.cookies["SID"] == "a"
    assert tokens.cookies["HSID"] == "b"
    assert tokens.cookies["SSID"] == "c"
    assert tokens.cookies["APISID"] == "d"
    assert tokens.cookies["SAPISID"] == "e"
