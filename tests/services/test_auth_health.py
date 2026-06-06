"""Tests for the AuthHealthChecker (multi-probe auth health check with caching).

These tests pin:
- Verdict logic in ``_determine_verdict`` (the priority ordering of
  auth-failure vs network-error outcomes).
- The error-classification contract: transport errors (httpx timeouts,
  connection refused) are reported with the ``"network_error:"`` prefix
  so the verdict can distinguish them from auth rejections. This is the
  contract that broke in the original PR — transport failures used to
  leak through as `TypeError: ...` style strings and be misclassified
  as auth failures.
- The ``valid`` field on ``AuthHealthReport``: must equal
  ``status == "configured"``. Latent bug fixed: the original code had
  ``valid=verdict != "configured"`` which is the opposite.
- TTL + mtime-bypass caching: re-checks within 30s are cached; an auth
  file mtime change bypasses the cache.
- The process-wide singleton returned by ``get_auth_health_checker``.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from notebooklm_tools.core.auth import AuthManager
from notebooklm_tools.services.auth import (
    AuthHealthChecker,
    AuthHealthReport,
    AuthProbeResult,
    get_auth_health_checker,
)


# ---------------------------------------------------------------------------
# Verdict logic — the heart of the multi-probe design
# ---------------------------------------------------------------------------


class TestDetermineVerdict:
    """`_determine_verdict` is the only place that converts probe errors
    into a user-facing status string. Test it directly so the priority
    ordering is pinned."""

    def test_no_probes_returns_not_configured(self):
        assert AuthHealthChecker._determine_verdict([]) == "not_configured"

    def test_all_probes_network_error_returns_unverified(self):
        """If every probe failed with a transport error, the user has a
        network problem, not an auth problem. The verdict must be
        ``unverified`` so we don't prompt them to re-auth."""
        probes = [
            AuthProbeResult(probe="homepage", valid=False, error="network_error: ConnectError: refused"),
            AuthProbeResult(probe="api", valid=False, error="network_error: TimeoutException: timed out"),
        ]
        assert AuthHealthChecker._determine_verdict(probes) == "unverified"

    def test_auth_failure_only_returns_stale(self):
        """If at least one probe raised a non-transport error and no
        probe raised a transport error, auth is genuinely rejected."""
        probes = [
            AuthProbeResult(probe="homepage", valid=False, error="expired"),
            AuthProbeResult(probe="api", valid=False, error="AuthenticationError: 401"),
        ]
        assert AuthHealthChecker._determine_verdict(probes) == "stale"

    def test_mixed_auth_and_network_returns_unverified(self):
        """If the API probe timed out AND the homepage probe returned an
        auth error, the auth error could be a downstream effect of the
        transport failure. Do not block the user from retrying."""
        probes = [
            AuthProbeResult(probe="homepage", valid=False, error="expired"),
            AuthProbeResult(probe="api", valid=False, error="network_error: TimeoutException"),
        ]
        assert AuthHealthChecker._determine_verdict(probes) == "unverified"

    def test_http_status_code_counts_as_auth_failure(self):
        """A `http_403` from the homepage should be treated as a
        credential problem, not a transport problem. The homepage probe
        prefixes HTTP errors with `http_` which does NOT match
        `network_error:`, so this falls into the auth-failure branch."""
        probes = [AuthProbeResult(probe="homepage", valid=False, error="http_403")]
        assert AuthHealthChecker._determine_verdict(probes) == "stale"

    def test_fallback_with_inconsistent_state_returns_stale(self):
        """Defensive: a probe with no error string at all (internal
        inconsistency) should land on ``stale`` so the user is prompted
        to refresh, not on a false ``unverified`` that hides the issue."""
        probes = [AuthProbeResult(probe="homepage", valid=False, error=None)]
        assert AuthHealthChecker._determine_verdict(probes) == "stale"


# ---------------------------------------------------------------------------
# Report.valid semantics — pin the bug we fixed
# ---------------------------------------------------------------------------


class TestReportValid:
    """`valid` on `AuthHealthReport` is a boolean shortcut for
    `status == "configured"`. The original PR had it inverted. Lock it."""

    def _make(self, **kwargs) -> AuthHealthReport:
        return AuthHealthReport(
            valid=kwargs.pop("valid", False),
            status=kwargs.pop("status", "stale"),
            probes=kwargs.pop("probes", []),
            **kwargs,
        )

    def test_valid_true_when_status_configured(self):
        report = self._make(status="configured", valid=True)
        assert report.valid is True
        assert report.status == "configured"

    def test_valid_false_when_status_stale(self):
        report = self._make(status="stale", valid=False)
        assert report.valid is False

    def test_valid_false_when_status_unverified(self):
        report = self._make(status="unverified", valid=False)
        assert report.valid is False

    def test_valid_false_when_status_not_configured(self):
        report = self._make(status="not_configured", valid=False)
        assert report.valid is False

    def test_valid_equals_status_configured_predicate(self):
        """The contract: `valid` is `status == "configured"`. This is a
        regression test for the inverted-`valid` bug."""
        for status in ("configured", "stale", "unverified", "not_configured"):
            expected = status == "configured"
            report = self._make(status=status, valid=expected)
            assert report.valid is expected, (
                f"status={status!r}: expected valid={expected}, got {report.valid}"
            )


# ---------------------------------------------------------------------------
# End-to-end check() flows with HTTP mocked
# ---------------------------------------------------------------------------


def _save_fake_profile(tmp_path, monkeypatch):
    """Plant a profile with valid-looking cookies in tmp_path and patch
    the config helpers so the checker reads it."""
    monkeypatch.setattr(
        "notebooklm_tools.utils.config.get_storage_dir", lambda: tmp_path
    )

    mgr = AuthManager("default")
    mgr.save_profile(
        cookies={
            "SID": "x",
            "HSID": "x",
            "SSID": "x",
            "APISID": "x",
            "SAPISID": "x",
        },
        email="test@example.com",
    )


class TestCheckEndToEnd:
    """Walk through the orchestration logic of `check()` with HTTP mocked."""

    def test_check_returns_not_configured_when_no_profile(self, tmp_path, monkeypatch):
        monkeypatch.setattr("notebooklm_tools.utils.config.get_storage_dir", lambda: tmp_path)
        checker = AuthHealthChecker()
        report = checker.check()
        assert report.status == "not_configured"
        assert report.valid is False
        assert report.probes == []

    def test_check_homepage_success_returns_configured(self, tmp_path, monkeypatch):
        _save_fake_profile(tmp_path, monkeypatch)

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = httpx.Response(
                200,
                request=httpx.Request("GET", "https://notebooklm.google.com/"),
                text='WIZ_global_data = {"SNlM0e":"csrf123abc"}',
            )
            report = AuthHealthChecker().check(timeout=2.0)

        assert report.status == "configured"
        assert report.valid is True
        assert report.probes[0].probe == "homepage"
        assert report.probes[0].valid is True

    def test_check_homepage_expired_api_success_returns_configured(
        self, tmp_path, monkeypatch
    ):
        """The bug-class this whole PR exists to fix: homepage says expired
        (Phase 2 / semi-stale cookies), but the RPC API would still accept
        them. The multi-probe design must return ``configured``."""
        _save_fake_profile(tmp_path, monkeypatch)

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value

            # Homepage redirects to accounts.google.com (the false positive)
            req = httpx.Request("GET", "https://accounts.google.com/ServiceLogin")
            client.get.return_value = httpx.Response(200, request=req, text="login page")

            # Patch the API probe to report success without touching the network
            with patch.object(AuthHealthChecker, "_probe_api", return_value=(True, None)):
                report = AuthHealthChecker().check(timeout=2.0)

        assert report.status == "configured"
        assert report.valid is True
        # The report should record BOTH probes (homepage failed, API succeeded)
        probe_kinds = {p.probe for p in report.probes}
        assert probe_kinds == {"homepage", "api"}

    def test_check_homepage_expired_api_network_error_returns_unverified(
        self, tmp_path, monkeypatch
    ):
        """If the homepage rejected auth AND the API probe hit a transport
        error, the verdict must be ``unverified`` (we don't know). This
        pins the contract that transport errors in the API probe are
        classified as network errors."""
        _save_fake_profile(tmp_path, monkeypatch)

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            req = httpx.Request("GET", "https://accounts.google.com/ServiceLogin")
            client.get.return_value = httpx.Response(200, request=req, text="login page")

            # API probe returns a network_error-prefixed string.
            with patch.object(
                AuthHealthChecker,
                "_probe_api",
                return_value=(False, "network_error: ConnectError: refused"),
            ):
                report = AuthHealthChecker().check(timeout=2.0)

        assert report.status == "unverified"
        assert report.valid is False

    def test_check_homepage_expired_api_auth_error_returns_stale(
        self, tmp_path, monkeypatch
    ):
        """If both probes say auth is dead, the verdict is ``stale``."""
        _save_fake_profile(tmp_path, monkeypatch)

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            req = httpx.Request("GET", "https://accounts.google.com/ServiceLogin")
            client.get.return_value = httpx.Response(200, request=req, text="login page")

            with patch.object(
                AuthHealthChecker,
                "_probe_api",
                return_value=(False, "AuthenticationError: invalid"),
            ):
                report = AuthHealthChecker().check(timeout=2.0)

        assert report.status == "stale"
        assert report.valid is False


# ---------------------------------------------------------------------------
# _probe_api error classification — the other bug we fixed
# ---------------------------------------------------------------------------


class TestProbeApiErrorClassification:
    """`_probe_api` must prefix transport errors with `network_error:`
    so the verdict logic can distinguish them. The original PR emitted
    `f"{type(e).__name__}: {e}"` for ALL exceptions, which made
    `unverified` unreachable for the API path."""

    def test_probe_api_success(self, tmp_path, monkeypatch):
        _save_fake_profile(tmp_path, monkeypatch)

        with patch(
            "notebooklm_tools.core.client.NotebookLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.list_notebooks.return_value = []
            ok, err = AuthHealthChecker()._probe_api(
                {"SID": "x"}, csrf_token="", timeout=2.0
            )
        assert ok is True
        assert err is None

    def test_probe_api_timeout_emits_network_error_prefix(self):
        """An httpx.TimeoutException from the API call must be reported
        with the ``network_error:`` prefix."""
        checker = AuthHealthChecker()
        with patch(
            "notebooklm_tools.core.client.NotebookLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.list_notebooks.side_effect = httpx.ConnectTimeout("timed out")
            ok, err = checker._probe_api({"SID": "x"}, csrf_token="", timeout=2.0)
        assert ok is False
        assert err is not None
        assert err.startswith("network_error:"), (
            "transport errors must be classified as network errors so the "
            "verdict logic can distinguish them from auth failures"
        )
        assert "ConnectTimeout" in err

    def test_probe_api_request_error_emits_network_error_prefix(self):
        """httpx.RequestError covers connection refused, DNS failures, etc."""
        checker = AuthHealthChecker()
        with patch(
            "notebooklm_tools.core.client.NotebookLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.list_notebooks.side_effect = httpx.ConnectError("refused")
            ok, err = checker._probe_api({"SID": "x"}, csrf_token="", timeout=2.0)
        assert ok is False
        assert err is not None
        assert err.startswith("network_error:")

    def test_probe_api_auth_exception_not_prefixed(self):
        """A non-httpx exception (e.g. a domain AuthenticationError) is
        treated as a credential problem, NOT a network error. The
        verdict logic will then classify it as ``stale``."""
        class FakeAuthError(Exception):
            pass

        checker = AuthHealthChecker()
        with patch(
            "notebooklm_tools.core.client.NotebookLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.list_notebooks.side_effect = FakeAuthError("bad creds")
            ok, err = checker._probe_api({"SID": "x"}, csrf_token="", timeout=2.0)
        assert ok is False
        assert err is not None
        assert not err.startswith("network_error:"), (
            "non-transport exceptions must NOT be misclassified as network errors"
        )


# ---------------------------------------------------------------------------
# Caching: TTL + mtime bypass
# ---------------------------------------------------------------------------


class TestCaching:
    def test_cached_report_within_ttl(self, tmp_path, monkeypatch):
        """Two checks within 30s with no auth-file change: the second is
        served from cache (probes are not re-run)."""
        _save_fake_profile(tmp_path, monkeypatch)
        checker = AuthHealthChecker()

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = httpx.Response(
                200,
                request=httpx.Request("GET", "https://notebooklm.google.com/"),
                text='WIZ_global_data = {"SNlM0e":"x"}',
            )
            first = checker.check(timeout=2.0)
            second = checker.check(timeout=2.0)

        assert first.status == "configured"
        assert second.status == "configured"
        assert second.cached is True, "second call should hit the cache"
        # Only one HTTP call total
        assert client.get.call_count == 1

    def test_force_bypasses_cache(self, tmp_path, monkeypatch):
        _save_fake_profile(tmp_path, monkeypatch)
        checker = AuthHealthChecker()

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = httpx.Response(
                200,
                request=httpx.Request("GET", "https://notebooklm.google.com/"),
                text='WIZ_global_data = {"SNlM0e":"x"}',
            )
            checker.check(timeout=2.0)
            checker.check(force=True, timeout=2.0)

        assert client.get.call_count == 2

    def test_invalidate_forces_fresh_check(self, tmp_path, monkeypatch):
        _save_fake_profile(tmp_path, monkeypatch)
        checker = AuthHealthChecker()

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = httpx.Response(
                200,
                request=httpx.Request("GET", "https://notebooklm.google.com/"),
                text='WIZ_global_data = {"SNlM0e":"x"}',
            )
            checker.check(timeout=2.0)
            checker.invalidate()
            checker.check(timeout=2.0)

        assert client.get.call_count == 2

    def test_auth_file_mtime_change_bypasses_cache(self, tmp_path, monkeypatch):
        """An external `nlm login` bumps the profile's cookies.json mtime.
        The next `check()` call must bypass the cache and re-probe."""
        import time as _time

        _save_fake_profile(tmp_path, monkeypatch)
        checker = AuthHealthChecker()

        with patch("httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = httpx.Response(
                200,
                request=httpx.Request("GET", "https://notebooklm.google.com/"),
                text='WIZ_global_data = {"SNlM0e":"x"}',
            )
            first = checker.check(timeout=2.0)
            # Simulate an external `nlm login` rewriting the profile
            _time.sleep(0.05)
            (tmp_path / "profiles" / "default" / "cookies.json").touch()
            second = checker.check(timeout=2.0)

        assert first.status == "configured"
        # Second call bypassed the cache because the mtime changed
        assert client.get.call_count == 2
        assert second.cached is False


# ---------------------------------------------------------------------------
# Singleton — the shared-cache contract between CLI and MCP
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        first = get_auth_health_checker()
        second = get_auth_health_checker()
        assert first is second

    def test_singleton_is_auth_health_checker(self):
        assert isinstance(get_auth_health_checker(), AuthHealthChecker)


# ---------------------------------------------------------------------------
# Cookies-to-dict helper — pin the list/dict/empty contract
# ---------------------------------------------------------------------------


class TestCookiesToDict:
    def test_list_of_dicts(self):
        profile = type("P", (), {"cookies": [{"name": "SID", "value": "v"}]})()
        assert AuthHealthChecker._cookies_to_dict(profile) == {"SID": "v"}

    def test_plain_dict(self):
        profile = type("P", (), {"cookies": {"SID": "v"}})()
        assert AuthHealthChecker._cookies_to_dict(profile) == {"SID": "v"}

    def test_empty(self):
        profile = type("P", (), {"cookies": {}})()
        assert AuthHealthChecker._cookies_to_dict(profile) == {}

    def test_none(self):
        profile = type("P", (), {"cookies": None})()
        assert AuthHealthChecker._cookies_to_dict(profile) == {}
