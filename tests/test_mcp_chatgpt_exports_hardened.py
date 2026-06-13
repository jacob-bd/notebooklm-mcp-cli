"""Tests for hardened outbound ChatGPT export links."""

from pathlib import Path
from unittest.mock import MagicMock

from notebooklm_tools.mcp.tools import chatgpt_exports


def test_export_bridge_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED", raising=False)
    result = chatgpt_exports.chatgpt_prepare_artifact_download(
        notebook_id="nb-1",
        artifact_type="report",
        confirm=True,
    )
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_export_bridge_requires_public_base_url(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED", "true")
    monkeypatch.delenv("NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL", raising=False)
    result = chatgpt_exports.chatgpt_prepare_artifact_download(
        notebook_id="nb-1",
        artifact_type="report",
        confirm=True,
    )
    assert result["status"] == "error"
    assert "base URL" in result["error"]


def test_export_bridge_requires_confirmation(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL", "https://example.test")
    result = chatgpt_exports.chatgpt_prepare_artifact_download(
        notebook_id="nb-1",
        artifact_type="report",
        confirm=False,
    )
    assert result["status"] == "pending_confirmation"
    assert result["settings"]["artifact_type"] == "report"


def test_register_and_claim_one_time_export(tmp_path):
    path = tmp_path / "report.md"
    path.write_text("hello")
    record = chatgpt_exports._register_export(path, "report.md", ttl_seconds=60, max_downloads=1)

    claimed, delete_after = chatgpt_exports.claim_chatgpt_export(record["token"])
    assert claimed is not None
    assert claimed["path"] == str(path)
    assert delete_after is True

    claimed_again, _ = chatgpt_exports.claim_chatgpt_export(record["token"])
    assert claimed_again is None


def test_prepare_artifact_download_stages_tokenized_link(monkeypatch, tmp_path):
    out_dir = tmp_path / "exports"
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL", "https://mcp.example.test")
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORT_CACHE_DIR", str(out_dir))
    monkeypatch.setattr(chatgpt_exports, "get_client", lambda: MagicMock())

    async def _download_async(_client, _notebook_id, _artifact_type, output_path, **_kwargs):
        Path(output_path).write_text("artifact")
        return {"artifact_type": _artifact_type, "path": output_path}

    monkeypatch.setattr(chatgpt_exports.downloads_service, "download_async", _download_async)

    result = chatgpt_exports.chatgpt_prepare_artifact_download(
        notebook_id="nb-1",
        artifact_type="report",
        confirm=True,
        ttl_seconds=60,
    )

    assert result["status"] == "success"
    assert result["download_url"].startswith("https://mcp.example.test/chatgpt-exports/")
    assert result["route_path"].startswith("/chatgpt-exports/")
    assert result["file_name"].startswith("notebooklm-report-")
    assert "path" not in result


class _FakeRequest:
    def __init__(self, token: str):
        self.path_params = {"token": token}


def _clear_export_records() -> None:
    with chatgpt_exports._records_lock:
        chatgpt_exports._records.clear()


def test_export_route_returns_404_for_expired_token(tmp_path):
    import asyncio
    import time

    from notebooklm_tools.mcp.server import chatgpt_export_download

    _clear_export_records()
    path = tmp_path / "expired.md"
    path.write_text("expired")
    record = chatgpt_exports._register_export(path, "expired.md", ttl_seconds=60, max_downloads=1)
    with chatgpt_exports._records_lock:
        chatgpt_exports._records[record["token"]]["expires_at"] = time.time() - 1

    response = asyncio.run(chatgpt_export_download(_FakeRequest(record["token"])))

    assert response.status_code == 404
    assert not path.exists()


def test_export_route_enforces_one_time_download_token(tmp_path):
    import asyncio

    from notebooklm_tools.mcp.server import chatgpt_export_download

    _clear_export_records()
    path = tmp_path / "once.md"
    path.write_text("once")
    record = chatgpt_exports._register_export(path, "once.md", ttl_seconds=60, max_downloads=1)

    first = asyncio.run(chatgpt_export_download(_FakeRequest(record["token"])))
    second = asyncio.run(chatgpt_export_download(_FakeRequest(record["token"])))

    assert first.status_code == 200
    assert second.status_code == 404


def test_export_route_allows_configured_multi_download_before_expiry(tmp_path):
    import asyncio

    from notebooklm_tools.mcp.server import chatgpt_export_download

    _clear_export_records()
    path = tmp_path / "twice.md"
    path.write_text("twice")
    record = chatgpt_exports._register_export(path, "twice.md", ttl_seconds=60, max_downloads=2)

    first = asyncio.run(chatgpt_export_download(_FakeRequest(record["token"])))
    second = asyncio.run(chatgpt_export_download(_FakeRequest(record["token"])))
    third = asyncio.run(chatgpt_export_download(_FakeRequest(record["token"])))

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 404


def test_prepare_artifact_download_rejects_and_deletes_oversized_file(monkeypatch, tmp_path):
    out_dir = tmp_path / "exports"
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL", "https://mcp.example.test")
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORT_CACHE_DIR", str(out_dir))
    monkeypatch.setenv("NOTEBOOKLM_CHATGPT_EXPORT_MAX_BYTES", "3")
    monkeypatch.setattr(chatgpt_exports, "get_client", lambda: MagicMock())

    async def _download_async(_client, _notebook_id, _artifact_type, output_path, **_kwargs):
        Path(output_path).write_text("too large")
        return {"artifact_type": _artifact_type, "path": output_path}

    monkeypatch.setattr(chatgpt_exports.downloads_service, "download_async", _download_async)

    result = chatgpt_exports.chatgpt_prepare_artifact_download(
        notebook_id="nb-1",
        artifact_type="report",
        confirm=True,
        ttl_seconds=60,
    )

    assert result["status"] == "error"
    assert "MAX_BYTES" in result["error"]
    assert not list(out_dir.glob("*"))
