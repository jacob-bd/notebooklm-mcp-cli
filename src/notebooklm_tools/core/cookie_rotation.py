"""Google auth cookie rotation helpers.

NotebookLM RPC traffic alone does not refresh Google's short-lived session
cookies.  A best-effort POST to Google's identity RotateCookies endpoint
refreshes the ``*SIDCC`` session cookies, which helps keep a session warm.

Note: this endpoint does NOT refresh the ``*PSIDTS`` freshness cookies from a
plain ``httpx`` client — Google only reissues those to a real browser session
(measured in issue #316).  Reviving an aged-out ``*PSIDTS`` requires the
headless-browser refresh in the auth-recovery path, not this call.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ROTATE_COOKIES_URL = "https://accounts.google.com/RotateCookies"
ROTATE_COOKIES_HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://accounts.google.com",
}
ROTATE_COOKIES_BODY = '[000,"-0000000000000000000"]'
DISABLE_ROTATE_COOKIES_ENV = "NOTEBOOKLM_DISABLE_ROTATE_COOKIES"
ROTATION_RATE_LIMIT_SECONDS = 60.0
ROTATION_PRECISION_TOLERANCE_SECONDS = 2.0

_last_rotation_by_key: dict[str, float] = {}
_rotation_lock = threading.Lock()


@dataclass
class CookieRotationResult:
    """Outcome of a best-effort RotateCookies request."""

    attempted: bool
    success: bool
    status_code: int | None = None
    skipped_reason: str | None = None
    error: str | None = None


def _rate_limit_key(storage_path: Path | None) -> str:
    return str(storage_path) if storage_path else "__process__"


def _recent_by_file_mtime(storage_path: Path | None) -> bool:
    """Return True when the auth storage file changed very recently."""
    if storage_path is None:
        return False
    try:
        age = time.time() - storage_path.stat().st_mtime
    except OSError:
        return False
    return -ROTATION_PRECISION_TOLERANCE_SECONDS <= age <= ROTATION_RATE_LIMIT_SECONDS


def _claim_rotation_attempt(storage_path: Path | None) -> bool:
    """Process-local guard to avoid hammering accounts.google.com."""
    key = _rate_limit_key(storage_path)
    now = time.monotonic()
    with _rotation_lock:
        last = _last_rotation_by_key.get(key)
        if last is not None and now - last <= ROTATION_RATE_LIMIT_SECONDS:
            return False
        _last_rotation_by_key[key] = now
        return True


def rotate_google_cookies(
    client: httpx.Client,
    *,
    storage_path: Path | None = None,
    timeout: float = 15.0,
    force: bool = False,
) -> CookieRotationResult:
    """Best-effort Google session-cookie rotation.

    Args:
        client: HTTP client with the Google cookie jar to rotate.
        storage_path: Optional auth file path used for rate limiting.
        timeout: Request timeout in seconds.
        force: Bypass file/process rate-limit guards.

    Returns:
        A ``CookieRotationResult``.  Failures are non-fatal by design; callers
        should continue with their normal auth check.
    """
    if os.environ.get(DISABLE_ROTATE_COOKIES_ENV) == "1":
        return CookieRotationResult(
            attempted=False,
            success=False,
            skipped_reason=f"{DISABLE_ROTATE_COOKIES_ENV}=1",
        )

    if not force:
        if _recent_by_file_mtime(storage_path):
            return CookieRotationResult(
                attempted=False,
                success=False,
                skipped_reason="recent_auth_storage",
            )
        if not _claim_rotation_attempt(storage_path):
            return CookieRotationResult(
                attempted=False,
                success=False,
                skipped_reason="recent_process_attempt",
            )

    try:
        response = client.post(
            ROTATE_COOKIES_URL,
            headers=ROTATE_COOKIES_HEADERS,
            content=ROTATE_COOKIES_BODY,
            follow_redirects=True,
            timeout=timeout,
        )
        response.raise_for_status()
        return CookieRotationResult(
            attempted=True,
            success=True,
            status_code=response.status_code,
        )
    except httpx.HTTPError as exc:
        logger.debug("RotateCookies POST failed (non-fatal): %s", exc)
        status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        return CookieRotationResult(
            attempted=True,
            success=False,
            status_code=status_code,
            error=f"{type(exc).__name__}: {exc}",
        )


def cookie_jar_to_list(cookie_jar: httpx.Cookies) -> list[dict[str, Any]]:
    """Convert an ``httpx.Cookies`` jar into the profile cookie-list shape."""
    cookies: list[dict[str, Any]] = []
    for cookie in cookie_jar.jar:
        item: dict[str, Any] = {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path or "/",
        }
        if cookie.expires is not None:
            item["expires"] = cookie.expires
        cookies.append(item)
    return cookies


def cookie_jar_to_dict(cookie_jar: httpx.Cookies) -> dict[str, str]:
    """Convert a cookie jar to a flat dict, preferring ``.google.com`` values."""
    out: dict[str, str] = {}
    google_locked: set[str] = set()
    for cookie in cookie_jar.jar:
        domain = (cookie.domain or "").lstrip(".").lower()
        is_google = domain == "google.com"
        if cookie.name in google_locked and not is_google:
            continue
        out[cookie.name] = cookie.value
        if is_google:
            google_locked.add(cookie.name)
    return out


def snapshot_cookie_input(
    original: dict[str, str] | list[dict[str, Any]], cookie_jar: httpx.Cookies
) -> dict[str, str] | list[dict[str, Any]]:
    """Snapshot a rotated jar using the same broad shape as the original input."""
    if isinstance(original, list):
        return cookie_jar_to_list(cookie_jar)
    return cookie_jar_to_dict(cookie_jar)
