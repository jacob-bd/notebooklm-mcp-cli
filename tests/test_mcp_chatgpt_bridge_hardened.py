"""Tests for the hardened, opt-in ChatGPT file bridge."""

from unittest.mock import MagicMock

import pytest

from notebooklm_tools.mcp.tools import chatgpt_bridge
from notebooklm_tools.services import ValidationError


def test_chatgpt_bridge_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED", raising=False)
    result = chatgpt_bridge.chatgpt_add_file_source(
        notebook_id="nb-1",
        download_url="https://files.example.com/doc.pdf",
        file_name="doc.pdf",
        confirm=True,
    )
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_chatgpt_bridge_status_reports_disabled(monkeypatch):
    monkeypatch.delenv("NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED", raising=False)
    result = chatgpt_bridge.chatgpt_bridge_status()
    assert result["status"] == "success"
    assert result["enabled"] is False


def test_validate_remote_url_requires_allowlist(monkeypatch):
    monkeypatch.setattr(chatgpt_bridge, "_public_ip_check", lambda _host: None)
    with pytest.raises(ValidationError, match="allowlist"):
        chatgpt_bridge._validate_remote_url("https://files.example.com/doc.pdf", [])


def test_validate_remote_url_rejects_non_https(monkeypatch):
    monkeypatch.setattr(chatgpt_bridge, "_public_ip_check", lambda _host: None)
    with pytest.raises(ValidationError, match="https"):
        chatgpt_bridge._validate_remote_url("http://files.example.com/doc.pdf", ["files.example.com"])


def test_validate_remote_url_rejects_private_ip_even_when_allowlisted():
    with pytest.raises(ValidationError, match="non-public"):
        chatgpt_bridge._validate_remote_url("https://127.0.0.1/doc.pdf", ["127.0.0.1"])


def test_validate_remote_url_accepts_exact_allowlisted_host(monkeypatch):
    monkeypatch.setattr(chatgpt_bridge, "_public_ip_check", lambda _host: None)
    assert (
        chatgpt_bridge._validate_remote_url(
            "https://files.example.com/doc.pdf", ["files.example.com"]
        )
        == "https://files.example.com/doc.pdf"
    )


def test_safe_filename_rejects_unsupported_extension():
    with pytest.raises(ValidationError, match="extension"):
        chatgpt_bridge._safe_filename("payload.exe")


def test_add_file_source_requires_confirmation(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED", "true")
    result = chatgpt_bridge.chatgpt_add_file_source(
        notebook_id="nb-1",
        download_url="https://files.example.com/doc.pdf",
        file_name="doc.pdf",
        confirm=False,
    )
    assert result["status"] == "pending_confirmation"


def test_add_file_source_deletes_temp_file_by_default(monkeypatch, tmp_path):
    temp_file = tmp_path / "doc.pdf"
    temp_file.write_bytes(b"pdf")
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED", "true")
    monkeypatch.setattr(chatgpt_bridge, "_download_remote_file", lambda *_args: (temp_file, 3))
    monkeypatch.setattr(chatgpt_bridge, "get_client", lambda: MagicMock())
    monkeypatch.setattr(
        chatgpt_bridge.sources_service,
        "add_source",
        lambda *_args, **_kwargs: {
            "source_type": "file",
            "source_id": "src-1",
            "title": "doc.pdf",
        },
    )

    result = chatgpt_bridge.chatgpt_add_file_source(
        notebook_id="nb-1",
        download_url="https://files.example.com/doc.pdf",
        file_name="doc.pdf",
        confirm=True,
    )

    assert result["status"] == "success"
    assert result["bytes_downloaded"] == 3
    assert result["local_file_retained"] is False
    assert not temp_file.exists()
