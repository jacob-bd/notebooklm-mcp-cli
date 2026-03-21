"""Targeted tests for server tool behaviors."""

import sys
import types
from pathlib import Path

from notebooklm_mcp.api_client import Notebook, extract_cookies_from_chrome_export, parse_timestamp
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


def test_parse_timestamp_returns_iso_utc_string():
    """parse_timestamp should convert epoch seconds into a stable ISO string."""
    assert parse_timestamp([1_706_748_123, 0]) == "2024-02-01T00:42:03Z"


def test_parse_timestamp_rejects_invalid_shapes():
    """parse_timestamp should return None for unsupported timestamp payloads."""
    assert parse_timestamp(None) is None
    assert parse_timestamp([]) is None
    assert parse_timestamp(["bad"]) is None


def test_extract_cookies_from_chrome_export_keeps_embedded_equals():
    """Cookie parsing should trim whitespace without breaking values containing '='."""
    cookies = extract_cookies_from_chrome_export("SID = a ; token = abc== ; HSID=b")

    assert cookies == {"SID": "a", "token": "abc==", "HSID": "b"}


def test_compact_research_result_truncates_report_and_sources():
    """Compact research results should keep enough context while shrinking large payloads."""
    result = {
        "report": "x" * 550,
        "sources": [{"id": idx} for idx in range(12)],
    }

    compact = server._compact_research_result(result)

    assert compact["report"].startswith("x" * 500)
    assert "... (truncated 50 characters." in compact["report"]
    assert len(compact["sources"]) == 10
    assert compact["sources_truncated"] == (
        "Showing first 10 of 12 sources. Set compact=False for all sources."
    )


def test_notebook_list_compact_counts_and_truncates_titles(monkeypatch):
    """notebook_list should expose counts and trim long titles in compact mode."""

    class FakeClient:
        def list_notebooks(self):
            return [
                Notebook(
                    id="owned-notebook",
                    title="A" * 55,
                    source_count=2,
                    sources=[],
                    is_owned=True,
                    is_shared=True,
                ),
                Notebook(
                    id="shared-notebook",
                    title="Shared notes",
                    source_count=1,
                    sources=[],
                    is_owned=False,
                    is_shared=False,
                ),
            ]

    monkeypatch.setattr(server, "get_client", lambda: FakeClient())

    result = server.notebook_list()

    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["owned_count"] == 1
    assert result["shared_count"] == 1
    assert result["shared_by_me_count"] == 1
    assert result["notebooks"][0]["title"] == ("A" * 50) + "..."
    assert result["notebooks"][1]["title"] == "Shared notes"
