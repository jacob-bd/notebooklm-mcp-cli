"""Disabled-by-default hardened helpers for ChatGPT file handoff.

This module intentionally does not expose a public file-serving route and does
not alter ordinary source/download tools. It only downloads remote files when an
explicit ChatGPT bridge tool is called and the bridge is enabled by environment.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import time
from contextlib import suppress
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from ...services import ServiceError, ValidationError
from ...services import sources as sources_service
from ...utils.config import get_data_dir
from ._utils import ResultDict, error_result, get_client, logged_tool

_FALSY = {"0", "false", "no", "off", ""}
_DEFAULT_MAX_BYTES = 25 * 1024 * 1024
_DEFAULT_TTL_SECONDS = 3600
_MAX_REDIRECTS = 3

_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".docx",
    ".csv",
    ".epub",
    ".mp3",
    ".m4a",
    ".wav",
    ".aac",
    ".ogg",
    ".opus",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSY


def _enabled() -> bool:
    return _env_bool("NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED", False)


def _allowed_hosts() -> list[str]:
    raw = os.environ.get("NOTEBOOKLM_CHATGPT_FILE_HOST_ALLOWLIST", "")
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def _max_bytes() -> int:
    raw = os.environ.get("NOTEBOOKLM_CHATGPT_FILE_MAX_BYTES", str(_DEFAULT_MAX_BYTES))
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_MAX_BYTES


def _cache_dir() -> Path:
    return Path(
        os.environ.get("NOTEBOOKLM_CHATGPT_FILE_CACHE_DIR", "")
        or get_data_dir() / "chatgpt_file_bridge"
    )


def _ttl_seconds() -> int:
    raw = os.environ.get("NOTEBOOKLM_CHATGPT_FILE_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_TTL_SECONDS


def _host_allowed(hostname: str, allowed_hosts: list[str]) -> bool:
    host = hostname.lower().rstrip(".")
    for pattern in allowed_hosts:
        pattern = pattern.lower().rstrip(".")
        if pattern.startswith("*."):
            suffix = pattern[1:]
            if host.endswith(suffix) and host != pattern[2:]:
                return True
        elif host == pattern:
            return True
    return False


def _public_ip_check(hostname: str) -> None:
    try:
        ipaddress.ip_address(hostname)
        addresses = [hostname]
    except ValueError:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        addresses = [info[4][0] for info in infos]

    if not addresses:
        raise ValidationError("URL host did not resolve to any address.")

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        ):
            raise ValidationError("URL host resolves to a non-public address.")


def _validate_remote_url(url: str, allowed_hosts: list[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValidationError("Only https:// ChatGPT file URLs are allowed.")
    if not parsed.hostname:
        raise ValidationError("URL must include a hostname.")
    if not allowed_hosts:
        raise ValidationError(
            "No ChatGPT file host allowlist configured. Set NOTEBOOKLM_CHATGPT_FILE_HOST_ALLOWLIST."
        )
    if not _host_allowed(parsed.hostname, allowed_hosts):
        raise ValidationError("URL host is not in NOTEBOOKLM_CHATGPT_FILE_HOST_ALLOWLIST.")

    _public_ip_check(parsed.hostname)
    return url


def _safe_filename(name: str | None, fallback: str = "chatgpt-file") -> str:
    raw = Path(name or fallback).name.strip().strip(".") or fallback
    safe = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in raw)
    suffix = Path(safe).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File extension '{suffix or '[none]'}' is not allowed for ChatGPT bridge uploads."
        )
    return safe[:180]


def cleanup_chatgpt_bridge_cache(max_age_seconds: int | None = None) -> int:
    """Delete stale files from the explicit ChatGPT bridge cache."""
    cutoff = time.time() - (max_age_seconds if max_age_seconds is not None else _ttl_seconds())
    removed = 0
    directory = _cache_dir()
    if not directory.exists():
        return 0
    for path in directory.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _download_remote_file(download_url: str, file_name: str | None) -> tuple[Path, int]:
    allowed_hosts = _allowed_hosts()
    current_url = _validate_remote_url(download_url, allowed_hosts)
    filename = _safe_filename(file_name or Path(urlparse(current_url).path).name)
    max_bytes = _max_bytes()
    directory = _cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{int(time.time())}-{os.urandom(4).hex()}-{filename}"

    total = 0
    try:
        for _redirect in range(_MAX_REDIRECTS + 1):
            with httpx.stream("GET", current_url, follow_redirects=False, timeout=30.0) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        raise ValidationError(
                            "Redirect response did not include a Location header."
                        )
                    current_url = _validate_remote_url(
                        urljoin(current_url, location), allowed_hosts
                    )
                    continue

                resp.raise_for_status()
                content_length = resp.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise ValidationError(
                        "ChatGPT file is larger than NOTEBOOKLM_CHATGPT_FILE_MAX_BYTES."
                    )

                with target.open("wb") as handle:
                    for chunk in resp.iter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValidationError(
                                "ChatGPT file exceeded NOTEBOOKLM_CHATGPT_FILE_MAX_BYTES."
                            )
                        handle.write(chunk)
                return target, total
        raise ValidationError("Too many redirects while downloading ChatGPT file.")
    except Exception:
        with suppress(OSError):
            target.unlink(missing_ok=True)
        raise


@logged_tool()
def chatgpt_bridge_status() -> ResultDict:
    """Return current hardened ChatGPT file bridge configuration."""
    return {
        "status": "success",
        "enabled": _enabled(),
        "allowed_hosts": _allowed_hosts(),
        "max_bytes": _max_bytes(),
        "cache_dir": str(_cache_dir()),
        "ttl_seconds": _ttl_seconds(),
    }


@logged_tool()
def chatgpt_add_file_source(
    notebook_id: str,
    download_url: str,
    file_name: str,
    title: str | None = None,
    wait: bool = True,
    wait_timeout: float = 120.0,
    confirm: bool = False,
    delete_after_upload: bool = True,
) -> ResultDict:
    """Download an explicitly allowed ChatGPT file URL and add it as a source.

    The bridge is disabled by default. Enable it with
    NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED=true and configure a strict host allowlist
    in NOTEBOOKLM_CHATGPT_FILE_HOST_ALLOWLIST.
    """
    if not _enabled():
        return error_result(
            "ChatGPT file bridge is disabled.",
            hint="Set NOTEBOOKLM_CHATGPT_BRIDGE_ENABLED=true and configure NOTEBOOKLM_CHATGPT_FILE_HOST_ALLOWLIST.",
        )
    if not confirm:
        return {
            "status": "pending_confirmation",
            "message": "Confirm adding this ChatGPT-hosted file to NotebookLM.",
            "settings": {
                "notebook_id": notebook_id,
                "file_name": file_name,
                "title": title or file_name,
                "allowed_hosts": _allowed_hosts(),
                "max_bytes": _max_bytes(),
                "delete_after_upload": delete_after_upload,
            },
            "note": "Set confirm=True after verifying the file URL source is trusted.",
        }

    local_path: Path | None = None
    try:
        cleanup_chatgpt_bridge_cache()
        local_path, bytes_downloaded = _download_remote_file(download_url, file_name)
        result = sources_service.add_source(
            get_client(),
            notebook_id,
            "file",
            file_path=str(local_path),
            title=title or file_name,
            wait=wait,
            wait_timeout=wait_timeout,
        )
        payload = {
            "status": "success",
            **result,
            "bytes_downloaded": bytes_downloaded,
            "local_file_retained": not delete_after_upload,
        }
        return payload
    except ValidationError as e:
        return error_result(str(e))
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
    finally:
        if delete_after_upload and local_path is not None:
            with suppress(OSError):
                local_path.unlink(missing_ok=True)


@logged_tool()
def chatgpt_bridge_cleanup(max_age_seconds: int | None = None) -> ResultDict:
    """Delete stale files from the explicit ChatGPT bridge cache."""
    try:
        removed = cleanup_chatgpt_bridge_cache(max_age_seconds)
        return {"status": "success", "removed": removed, "cache_dir": str(_cache_dir())}
    except Exception as e:
        return error_result(str(e))
