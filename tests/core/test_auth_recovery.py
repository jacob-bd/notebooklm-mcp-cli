"""Regression tests for long-lived auth recovery (issue #316).

Covers two confirmed defects in ``BaseClient`` auth recovery:

1. Layer 2 (disk reload) blanks the CSRF token to force re-extraction, but the
   deep retry skipped Layer 1 — the only place that re-extracts it — so the
   retry went out with an empty ``at=`` token and failed even when valid
   cookies were already on disk.
2. ``_try_reload_or_headless_auth`` returned early whenever a profile existed
   on disk, so the headless-browser refresh (which actually revives an
   aged-out session) was never reached.
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from notebooklm_tools.core.auth import AuthTokens
from notebooklm_tools.core.client import AuthenticationError, NotebookLMClient


def _make_client(cookies):
    with patch.object(NotebookLMClient, "_refresh_auth_tokens"):
        return NotebookLMClient(cookies=cookies, csrf_token="stale_token")


def test_deep_retry_reextracts_csrf_after_disk_reload():
    """After Layer 2 loads fresh cookies, the deep retry must re-extract the CSRF.

    Without the fix the retry POSTs an empty ``at=`` token, gets a 400, and
    raises ``AuthenticationError`` even though valid cookies are on disk.
    """
    client = _make_client({"SID": "stale"})

    # The homepage refresh fails while the stale in-memory cookies are active
    # (login redirect) and succeeds once fresh cookies are loaded from disk.
    def refresh_side_effect():
        if client.cookies == {"SID": "stale"}:
            raise ValueError("Authentication expired. accounts.google.com login")
        client.csrf_token = "fresh_token"

    # Disk holds different (fresher) cookies than what is in memory.
    fresh_disk = AuthTokens(cookies={"SID": "fresh"}, extracted_at=2.0)

    req = httpx.Request("POST", "https://notebooklm.google.com/batchexecute")
    success_json = json.dumps([["wrb.fr", "rLM1Ne", '{"ok":1}']])
    success_text = f")]}}'\n{len(success_json)}\n{success_json}"

    def post_side_effect(url, content=None, timeout=None, **kwargs):
        # Google accepts the request only with fresh cookies AND a real token.
        if client.cookies == {"SID": "fresh"} and client.csrf_token:
            return httpx.Response(200, request=req, text=success_text)
        resp = httpx.Response(400, request=req)
        raise httpx.HTTPStatusError("Bad Request", request=req, response=resp)

    http_client = MagicMock(spec=httpx.Client)
    http_client.post.side_effect = post_side_effect

    with (
        patch.object(client, "_get_client", return_value=http_client),
        patch.object(client, "_refresh_auth_tokens", side_effect=refresh_side_effect) as refresh,
        patch(
            "notebooklm_tools.core.auth.load_cached_tokens",
            return_value=fresh_disk,
        ),
    ):
        result = client._call_rpc("rLM1Ne", [])

    assert result == {"ok": 1}
    # Called twice: once for Layer 1 (fails on stale cookies), once to
    # re-extract the CSRF after Layer 2 swapped in fresh disk cookies.
    assert refresh.call_count == 2
    assert client.csrf_token == "fresh_token"


def test_reload_prefers_headless_when_disk_cookies_unchanged():
    """When disk cookies match the known-bad ones, fall through to headless.

    Reloading identical cookies cannot help; only a headless refresh (which
    makes Google reissue the short-lived cookies) can revive the session.
    """
    client = _make_client({"SID": "stale"})

    same_disk = AuthTokens(cookies={"SID": "stale"}, extracted_at=1.0)
    headless_tokens = AuthTokens(
        cookies={"SID": "headless"},
        csrf_token="hcsrf",
        session_id="hsid",
        extracted_at=3.0,
    )

    with (
        patch(
            "notebooklm_tools.core.auth.load_cached_tokens",
            return_value=same_disk,
        ),
        patch(
            "notebooklm_tools.utils.auth_browser.run_headless_auth",
            return_value=headless_tokens,
        ) as headless,
    ):
        recovered = client._try_reload_or_headless_auth()

    assert recovered is True
    headless.assert_called_once()
    assert client.cookies == {"SID": "headless"}
    assert client.csrf_token == "hcsrf"
    assert client._session_id == "hsid"


def test_reload_uses_disk_when_cookies_differ():
    """When disk holds different cookies (external re-login), reload them.

    This preserves the existing recovery path and must NOT trigger headless.
    """
    client = _make_client({"SID": "stale"})

    fresh_disk = AuthTokens(cookies={"SID": "fresh"}, extracted_at=2.0)

    with (
        patch(
            "notebooklm_tools.core.auth.load_cached_tokens",
            return_value=fresh_disk,
        ),
        patch(
            "notebooklm_tools.utils.auth_browser.run_headless_auth",
        ) as headless,
    ):
        recovered = client._try_reload_or_headless_auth()

    assert recovered is True
    headless.assert_not_called()
    assert client.cookies == {"SID": "fresh"}
    # CSRF blanked so the deep retry re-extracts it against the fresh cookies.
    assert client.csrf_token == ""


def test_recovery_still_fails_cleanly_when_nothing_helps():
    """If disk cookies match and headless fails, surface AuthenticationError."""
    client = _make_client({"SID": "stale"})

    same_disk = AuthTokens(cookies={"SID": "stale"}, extracted_at=1.0)

    req = httpx.Request("POST", "https://notebooklm.google.com/batchexecute")

    def post_side_effect(url, content=None, timeout=None, **kwargs):
        resp = httpx.Response(400, request=req)
        raise httpx.HTTPStatusError("Bad Request", request=req, response=resp)

    http_client = MagicMock(spec=httpx.Client)
    http_client.post.side_effect = post_side_effect

    with (
        patch.object(client, "_get_client", return_value=http_client),
        patch.object(
            client,
            "_refresh_auth_tokens",
            side_effect=ValueError("Authentication expired. accounts.google.com"),
        ),
        patch(
            "notebooklm_tools.core.auth.load_cached_tokens",
            return_value=same_disk,
        ),
        patch(
            "notebooklm_tools.utils.auth_browser.run_headless_auth",
            return_value=None,
        ),
        pytest.raises(AuthenticationError, match="Authentication expired"),
    ):
        client._call_rpc("rLM1Ne", [])
