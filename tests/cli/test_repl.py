"""Tests for the interactive chat REPL."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

from notebooklm_tools.cli.commands import repl


def test_run_chat_repl_banner_uses_normalized_source_count(monkeypatch):
    client = MagicMock()
    client.get_notebook_sources_with_types.return_value = [
        {"id": "src-1", "title": "Source 1", "source_type_name": "text"},
        {"id": "src-2", "title": "Source 2", "source_type_name": "url"},
    ]

    panel_text = []

    monkeypatch.setattr(
        repl,
        "get_client",
        lambda profile=None: nullcontext(client),
    )
    monkeypatch.setattr(
        repl,
        "get_alias_manager",
        lambda: SimpleNamespace(resolve=lambda value: value),
    )
    monkeypatch.setattr(
        repl.notebook_service,
        "get_notebook",
        lambda _client, _notebook_id: {
            "title": "Notebook Title",
            "source_count": 2,
            "sources": [],
        },
    )
    monkeypatch.setattr(
        repl,
        "Panel",
        lambda renderable, **kwargs: panel_text.append(renderable) or renderable,
    )
    monkeypatch.setattr(repl.console, "input", lambda prompt: "/exit")
    monkeypatch.setattr(repl.console, "print", lambda *args, **kwargs: None)

    repl.run_chat_repl("nb-123")

    assert panel_text
    assert "2 source(s) loaded" in panel_text[0]
    client.get_notebook_sources_with_types.assert_called_once_with("nb-123")


def test_run_chat_repl_empty_notebook_skips_source_fetch(monkeypatch):
    client = MagicMock()

    panel_text = []

    monkeypatch.setattr(
        repl,
        "get_client",
        lambda profile=None: nullcontext(client),
    )
    monkeypatch.setattr(
        repl,
        "get_alias_manager",
        lambda: SimpleNamespace(resolve=lambda value: value),
    )
    monkeypatch.setattr(
        repl.notebook_service,
        "get_notebook",
        lambda _client, _notebook_id: {
            "title": "Empty Notebook",
            "source_count": 0,
            "sources": [],
        },
    )
    monkeypatch.setattr(
        repl,
        "Panel",
        lambda renderable, **kwargs: panel_text.append(renderable) or renderable,
    )
    monkeypatch.setattr(repl.console, "input", lambda prompt: "/exit")
    monkeypatch.setattr(repl.console, "print", lambda *args, **kwargs: None)

    repl.run_chat_repl("nb-empty")

    assert panel_text
    assert "0 source(s) loaded" in panel_text[0]
    client.get_notebook_sources_with_types.assert_not_called()
