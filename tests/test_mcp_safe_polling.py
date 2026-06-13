"""Tests for safe MCP polling behavior.

These tests intentionally verify that polling does not add ChatGPT-specific
side effects such as public file staging or download URLs.
"""

from unittest.mock import MagicMock

from notebooklm_tools.mcp.tools import downloads, sources
from notebooklm_tools.services import ServiceError


def test_source_get_content_polls_until_content(monkeypatch):
    calls = {"n": 0}

    def _get_source_content(_client, _source_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"content": "", "title": "Pending", "source_type": "text", "char_count": 0}
        return {"content": "ready", "title": "Ready", "source_type": "text", "char_count": 5}

    monkeypatch.setattr(sources, "get_client", lambda: MagicMock())
    monkeypatch.setattr(sources.sources_service, "get_source_content", _get_source_content)
    monkeypatch.setattr(sources.time, "sleep", lambda _seconds: None)

    result = sources.source_get_content("src-1", wait=True, wait_timeout=1, poll_interval=0.5)

    assert result["status"] == "success"
    assert result["content"] == "ready"
    assert "download_url" not in result
    assert calls["n"] == 2


def test_source_get_content_pending_without_disk_side_effect(monkeypatch):
    monkeypatch.setattr(sources, "get_client", lambda: MagicMock())
    monkeypatch.setattr(
        sources.sources_service,
        "get_source_content",
        lambda _client, _source_id: {
            "content": "",
            "title": "Pending",
            "source_type": "text",
            "char_count": 0,
        },
    )

    result = sources.source_get_content("src-1", wait=True, wait_timeout=0, poll_interval=0.5)

    assert result["status"] == "pending"
    assert "download_url" not in result


def test_download_artifact_polls_transient_service_error(monkeypatch, tmp_path):
    calls = {"n": 0}
    out = tmp_path / "audio.m4a"

    async def _download_async(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ServiceError("audio is complete, but its media download URL is still propagating")
        out.write_bytes(b"audio")
        return {"artifact_type": "audio", "path": str(out)}

    monkeypatch.setattr(downloads, "get_client", lambda: MagicMock())
    monkeypatch.setattr(downloads.downloads_service, "download_async", _download_async)
    monkeypatch.setattr(downloads.time, "sleep", lambda _seconds: None)

    result = downloads.download_artifact(
        notebook_id="nb-1",
        artifact_type="audio",
        output_path=str(out),
        wait=True,
        wait_timeout=1,
        poll_interval=0.5,
    )

    assert result["status"] == "success"
    assert result["path"] == str(out)
    assert "download_url" not in result
    assert calls["n"] == 2
