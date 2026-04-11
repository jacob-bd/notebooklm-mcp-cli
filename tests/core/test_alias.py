"""Tests for alias type detection."""

from contextlib import nullcontext
from unittest.mock import MagicMock

from notebooklm_tools.core.alias import detect_id_type
from notebooklm_tools.core.exceptions import NLMError


def test_detect_id_type_returns_notebook(monkeypatch):
    client = MagicMock()
    client.get_notebook.return_value = {"id": "nb-123"}

    monkeypatch.setattr(
        "notebooklm_tools.cli.utils.get_client",
        lambda profile=None: nullcontext(client),
    )

    assert detect_id_type("nb-123") == "notebook"


def test_detect_id_type_returns_source_without_legacy_method(monkeypatch):
    class SourceOnlyClient:
        def get_notebook(self, _value):
            raise NLMError("Notebook not found")

        def get_source_fulltext(self, _value):
            return {
                "content": "source body",
                "title": "Source Title",
                "type": "text",
            }

    monkeypatch.setattr(
        "notebooklm_tools.cli.utils.get_client",
        lambda profile=None: nullcontext(SourceOnlyClient()),
    )

    assert detect_id_type("src-123") == "source"


def test_detect_id_type_returns_unknown_when_source_lookup_fails(monkeypatch):
    client = MagicMock()
    client.get_notebook.side_effect = NLMError("Notebook not found")
    client.get_source_fulltext.side_effect = RuntimeError("boom")

    monkeypatch.setattr(
        "notebooklm_tools.cli.utils.get_client",
        lambda profile=None: nullcontext(client),
    )

    assert detect_id_type("missing-id") == "unknown"


def test_detect_id_type_returns_unknown_when_client_lacks_source_lookup(monkeypatch):
    class ClientWithoutSourceLookup:
        def get_notebook(self, _value):
            raise NLMError("Notebook not found")

    monkeypatch.setattr(
        "notebooklm_tools.cli.utils.get_client",
        lambda profile=None: nullcontext(ClientWithoutSourceLookup()),
    )

    assert detect_id_type("maybe-source") == "unknown"
