"""Hardened outbound ChatGPT download links for NotebookLM artifacts.

This module is intentionally separate from ordinary download tools. Existing
`download_artifact` behavior is unchanged; files are staged only when the
explicit outbound bridge tool is called and the feature is enabled.
"""

from __future__ import annotations

import asyncio
import mimetypes
import os
import secrets
import time
from contextlib import suppress
from pathlib import Path
from threading import Lock
from typing import Any

from ...services import ServiceError, ValidationError
from ...services import downloads as downloads_service
from ...utils.config import get_data_dir
from ._utils import ResultDict, error_result, get_client, logged_tool

_FALSY = {"0", "false", "no", "off", ""}
_DEFAULT_TTL_SECONDS = 600
_DEFAULT_MAX_BYTES = 100 * 1024 * 1024
_DEFAULT_MAX_DOWNLOADS = 1

_records: dict[str, dict[str, Any]] = {}
_records_lock = Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSY


def _enabled() -> bool:
    return _env_bool("NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED", False)


def _public_base_url() -> str:
    return os.environ.get("NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL", "").strip().rstrip("/")


def _cache_dir() -> Path:
    return Path(
        os.environ.get("NOTEBOOKLM_CHATGPT_EXPORT_CACHE_DIR", "")
        or get_data_dir() / "chatgpt_export_bridge"
    )


def _ttl_seconds(value: int | None = None) -> int:
    if value is not None:
        return max(1, int(value))
    raw = os.environ.get("NOTEBOOKLM_CHATGPT_EXPORT_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_TTL_SECONDS


def _max_bytes() -> int:
    raw = os.environ.get("NOTEBOOKLM_CHATGPT_EXPORT_MAX_BYTES", str(_DEFAULT_MAX_BYTES))
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_MAX_BYTES


def _safe_download_name(artifact_type: str, output_format: str, slide_deck_format: str) -> str:
    effective_format = slide_deck_format if artifact_type == "slide_deck" else output_format
    ext = downloads_service.get_default_extension(artifact_type, effective_format)
    stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in artifact_type)
    return f"notebooklm-{stem}-{secrets.token_hex(4)}.{ext}"


def cleanup_chatgpt_exports() -> int:
    """Remove expired staged export files and expired in-memory records."""
    now = time.time()
    removed = 0
    with _records_lock:
        expired = [token for token, record in _records.items() if record["expires_at"] <= now]
        for token in expired:
            record = _records.pop(token)
            with suppress(OSError):
                Path(record["path"]).unlink(missing_ok=True)
            removed += 1

    directory = _cache_dir()
    if directory.exists():
        cutoff = now - _ttl_seconds()
        for path in directory.iterdir():
            with suppress(OSError):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
    return removed


def _register_export(path: Path, file_name: str, ttl_seconds: int, max_downloads: int) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + ttl_seconds
    mime_type, _ = mimetypes.guess_type(file_name)
    record = {
        "token": token,
        "path": str(path),
        "file_name": file_name,
        "mime_type": mime_type or "application/octet-stream",
        "expires_at": expires_at,
        "downloads_remaining": max(1, max_downloads),
    }
    with _records_lock:
        _records[token] = record
    return record


def claim_chatgpt_export(token: str) -> tuple[dict[str, Any] | None, bool]:
    """Claim a staged export for the HTTP route.

    Returns `(record, delete_after_response)`. Last/one-time downloads are
    removed from the token registry before the response is served.
    """
    with _records_lock:
        record = _records.get(token)
        if not record:
            return None, False
        if record["expires_at"] <= time.time() or not Path(record["path"]).is_file():
            _records.pop(token, None)
            with suppress(OSError):
                Path(record["path"]).unlink(missing_ok=True)
            return None, False

        record["downloads_remaining"] -= 1
        delete_after_response = record["downloads_remaining"] <= 0
        if delete_after_response:
            _records.pop(token, None)
        return dict(record), delete_after_response


def delete_export_file(path: str) -> None:
    """Best-effort file deletion used by the HTTP route background task."""
    with suppress(OSError):
        Path(path).unlink(missing_ok=True)


@logged_tool()
def chatgpt_export_status() -> ResultDict:
    """Return current outbound ChatGPT export bridge status."""
    cleanup_chatgpt_exports()
    with _records_lock:
        active = len(_records)
    return {
        "status": "success",
        "enabled": _enabled(),
        "public_base_url_configured": bool(_public_base_url()),
        "cache_dir": str(_cache_dir()),
        "ttl_seconds": _ttl_seconds(),
        "max_bytes": _max_bytes(),
        "active_exports": active,
    }


@logged_tool()
def chatgpt_export_cleanup() -> ResultDict:
    """Clean expired staged ChatGPT export files."""
    try:
        return {"status": "success", "removed": cleanup_chatgpt_exports()}
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def chatgpt_prepare_artifact_download(
    notebook_id: str,
    artifact_type: str,
    artifact_id: str | None = None,
    output_format: str = "json",
    slide_deck_format: str = "pdf",
    ttl_seconds: int | None = None,
    max_downloads: int = _DEFAULT_MAX_DOWNLOADS,
    confirm: bool = False,
) -> ResultDict:
    """Stage a NotebookLM artifact behind a short-lived tokenized route.

    Disabled by default. This is the explicit outbound bridge and does not
    change `download_artifact` or any ordinary tool behavior.
    """
    if not _enabled():
        return error_result(
            "ChatGPT outbound export bridge is disabled.",
            hint="Set NOTEBOOKLM_CHATGPT_EXPORTS_ENABLED=true and NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL.",
        )
    base_url = _public_base_url()
    if not base_url:
        return error_result(
            "No public base URL configured for ChatGPT outbound exports.",
            hint="Set NOTEBOOKLM_CHATGPT_EXPORT_BASE_URL to the HTTPS tunnel origin for this MCP server.",
        )
    if not confirm:
        return {
            "status": "pending_confirmation",
            "message": "Confirm staging this NotebookLM artifact for a short-lived ChatGPT download.",
            "settings": {
                "notebook_id": notebook_id,
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "ttl_seconds": _ttl_seconds(ttl_seconds),
                "max_downloads": max(1, max_downloads),
                "max_bytes": _max_bytes(),
            },
            "note": "Set confirm=True after verifying this artifact should be exposed through the tunnel.",
        }
    try:
        cleanup_chatgpt_exports()
        downloads_service.validate_artifact_type(artifact_type)
        if artifact_type in downloads_service.INTERACTIVE_TYPES:
            downloads_service.validate_output_format(output_format)

        directory = _cache_dir()
        directory.mkdir(parents=True, exist_ok=True)
        file_name = _safe_download_name(artifact_type, output_format, slide_deck_format)
        output_path = directory / file_name
        max_bytes = _max_bytes()

        def _progress(current: int, _total: int) -> None:
            if current > max_bytes:
                raise ValidationError("Artifact exceeded NOTEBOOKLM_CHATGPT_EXPORT_MAX_BYTES.")

        result = asyncio.run(
            downloads_service.download_async(
                get_client(),
                notebook_id,
                artifact_type,
                str(output_path),
                artifact_id=artifact_id,
                output_format=output_format,
                progress_callback=_progress,
                slide_deck_format=slide_deck_format,
            )
        )
        final_path = Path(result["path"])
        size = final_path.stat().st_size
        if size > max_bytes:
            with suppress(OSError):
                final_path.unlink(missing_ok=True)
            raise ValidationError("Artifact exceeded NOTEBOOKLM_CHATGPT_EXPORT_MAX_BYTES.")

        record = _register_export(
            final_path,
            final_path.name,
            _ttl_seconds(ttl_seconds),
            max_downloads,
        )
        route_path = f"/chatgpt-exports/{record['token']}"
        return {
            "status": "success",
            "artifact_type": artifact_type,
            "path": str(final_path),
            "bytes": size,
            "expires_at": record["expires_at"],
            "downloads_remaining": record["downloads_remaining"],
            "download_url": f"{base_url}{route_path}",
            "route_path": route_path,
        }
    except ValidationError as e:
        return error_result(str(e))
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
