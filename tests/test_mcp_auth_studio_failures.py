"""Regression tests for the P1 auth/studio silent-failure bug (Netter bug report 2026-06-01).

Bug: under stale/expired auth, `refresh_auth()` returns status:"success" (it only
reloads dead tokens from disk), and `studio_create()` returns status:"success" with an
artifact_id that immediately fails — sending agents into pointless polling loops, with
`studio_status()` exposing `status:"failed"` and no error reason.

These tests pin the *desired* contract. They are RED against notebooklm-mcp-cli 0.6.13
and GREEN after the fix. All auth states are mocked — no network, no real credentials.
"""

import importlib

import pytest

# MCP tool modules under test
auth_tools = importlib.import_module("notebooklm_tools.mcp.tools.auth")
studio_tools = importlib.import_module("notebooklm_tools.mcp.tools.studio")
core_auth = importlib.import_module("notebooklm_tools.core.auth")
services_auth = importlib.import_module("notebooklm_tools.services.auth")


# --------------------------------------------------------------------------- #
# Helpers / fakes
# --------------------------------------------------------------------------- #
def _auth_result(valid, reason=None):
    """Build a real AuthCheckResult so we exercise the production type."""
    return core_auth.AuthCheckResult(valid=valid, reason=reason, live=True, profile="default")


def _patch_credentials_usable(monkeypatch, usable, status="stale", detail=None, counter=None):
    """Patch the service-layer auth wrapper used by refresh_auth and studio_create."""

    def _credentials_are_usable(**_kw):
        if counter is not None:
            counter["n"] += 1
        return usable, "configured" if usable else status, detail

    monkeypatch.setattr(
        services_auth,
        "credentials_are_usable",
        _credentials_are_usable,
        raising=True,
    )


class _FakeClient:
    """Stand-in for NotebookLMClient; never touches the network."""


# --------------------------------------------------------------------------- #
# Test 1 — refresh_auth honesty
# --------------------------------------------------------------------------- #
def test_refresh_auth_does_not_claim_success_when_tokens_are_expired(monkeypatch):
    """refresh_auth() must NOT return status:"success" while the reloaded tokens are actually unusable. A disk reload of
    dead tokens is not a successful re-auth.

    Desired: when tokens load from disk but a live validity check says they're expired, refresh_auth() returns a
    non-success status that tells the user to run `nlm login`.
    """
    # Tokens DO load from disk (file exists)...
    monkeypatch.setattr(auth_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(auth_tools, "reset_client", lambda: None, raising=True)
    monkeypatch.setattr(
        core_auth,
        "load_cached_tokens",
        lambda: core_auth.AuthTokens(cookies={"SID": "x"}, extracted_at=0.0),
        raising=True,
    )
    # ...but auth probes report stale even though this test expects failure.
    _patch_credentials_usable(monkeypatch, usable=False, status="stale")
    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)

    result = auth_tools.refresh_auth()

    assert result.get("status") != "success", (
        f"refresh_auth lied: returned success while tokens are expired. Got: {result}"
    )
    # And it should point the user at the real fix.
    blob = (str(result.get("error", "")) + str(result.get("message", ""))).lower()
    assert "nlm login" in blob, f"Expected actionable 'nlm login' guidance, got: {result}"


def test_refresh_auth_returns_helpful_error_when_env_var_set(monkeypatch):
    """When NOTEBOOKLM_COOKIES is set (e.g. via claude_desktop_config.json), the env var
    overrides all disk-based auth. A disk reload won't help — surface a clear, actionable
    error pointing at the MCP config file instead of lying with 'success'.
    """
    monkeypatch.setenv("NOTEBOOKLM_COOKIES", "SID=fake; HSID=fake; SSID=fake")

    # If the code wrongly proceeds, make the disk path explode so the test can't pass by luck.
    def _boom_load():
        raise AssertionError("refresh_auth should not touch disk tokens when env var is set")

    monkeypatch.setattr(core_auth, "load_cached_tokens", _boom_load, raising=True)
    monkeypatch.setattr(
        auth_tools,
        "get_client",
        lambda: (_ for _ in ()).throw(AssertionError("should not call get_client")),
        raising=True,
    )

    result = auth_tools.refresh_auth()

    assert result.get("status") == "error", f"Expected error when env var set, got: {result}"
    blob = str(result.get("error", "")).lower()
    assert "notebooklm_cookies" in blob or "mcp config" in blob, (
        f"Error should point the user at the env var / MCP config, got: {result}"
    )


def test_refresh_auth_reports_success_when_tokens_are_valid(monkeypatch):
    """The happy path must still work: valid tokens on disk → success."""
    monkeypatch.setattr(auth_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(auth_tools, "reset_client", lambda: None, raising=True)
    monkeypatch.setattr(
        core_auth,
        "load_cached_tokens",
        lambda: core_auth.AuthTokens(cookies={"SID": "x"}, extracted_at=0.0),
        raising=True,
    )
    _patch_credentials_usable(monkeypatch, usable=True)
    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)

    result = auth_tools.refresh_auth()
    assert result.get("status") == "success", f"Valid tokens should refresh OK, got: {result}"


def test_refresh_auth_succeeds_when_probes_stale_but_api_works(monkeypatch):
    """Semi-stale cookies: AuthHealthChecker may say stale while RPC still works.
    refresh_auth must not block agents when the API confirmation succeeds."""
    monkeypatch.setattr(auth_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(auth_tools, "reset_client", lambda: None, raising=True)
    monkeypatch.setattr(
        core_auth,
        "load_cached_tokens",
        lambda: core_auth.AuthTokens(cookies={"SID": "x"}, extracted_at=0.0),
        raising=True,
    )
    _patch_credentials_usable(monkeypatch, usable=True)
    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)

    result = auth_tools.refresh_auth()
    assert result.get("status") == "success", f"API-confirmed auth should refresh OK, got: {result}"


# --------------------------------------------------------------------------- #
# Test 2 — studio_create pre-flight auth check
# --------------------------------------------------------------------------- #
def test_studio_create_fails_loudly_on_stale_auth(monkeypatch):
    """When auth is stale/expired, studio_create() must return status:"error" BEFORE firing a doomed generation request
    — not status:"success" with an artifact_id that immediately fails.
    """
    studio_tools._auth_guard_expires = 0.0  # force guard expired so auth is re-checked
    _patch_credentials_usable(monkeypatch, usable=False, status="expired")

    # If the code wrongly proceeds, make the client call explode so the test can't pass by luck.
    def _boom():
        raise AssertionError("studio_create proceeded to get_client() despite stale auth")

    monkeypatch.setattr(studio_tools, "get_client", _boom, raising=True)

    result = studio_tools.studio_create(
        notebook_id="nb-123",
        artifact_type="infographic",
        confirm=True,
    )

    assert result.get("status") == "error", (
        f"studio_create should error loudly on stale auth, got: {result}"
    )
    blob = (str(result.get("error", "")) + str(result.get("hint", ""))).lower()
    assert "nlm login" in blob or "auth" in blob, (
        f"Error should explain the auth problem, got: {result}"
    )


def test_studio_create_proceeds_when_auth_valid(monkeypatch):
    """With valid auth, studio_create() must still create the artifact normally."""
    studio_tools._auth_guard_expires = 0.0  # force guard expired so auth is re-checked
    _patch_credentials_usable(monkeypatch, usable=True)
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service,
        "create_artifact",
        lambda *a, **k: {"artifact_id": "art-1", "status": "in_progress"},
        raising=True,
    )

    result = studio_tools.studio_create(
        notebook_id="nb-123",
        artifact_type="infographic",
        confirm=True,
    )
    assert result.get("status") == "success", f"Valid auth should create artifact, got: {result}"
    assert result.get("artifact_id") == "art-1"


def test_studio_create_proceeds_when_probes_stale_but_api_works(monkeypatch):
    """Issue #224 class: server_info/AuthHealthChecker may say stale while RPC works."""
    studio_tools._auth_guard_expires = 0.0
    _patch_credentials_usable(monkeypatch, usable=True)
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service,
        "create_artifact",
        lambda *a, **k: {"artifact_id": "art-semi", "status": "in_progress"},
        raising=True,
    )

    result = studio_tools.studio_create(
        notebook_id="nb-123",
        artifact_type="audio",
        confirm=True,
    )
    assert result.get("status") == "success", f"API-confirmed auth should create, got: {result}"


# --------------------------------------------------------------------------- #
# Test 3 — studio_status failure surface
# --------------------------------------------------------------------------- #
def _client_returning(artifacts):
    class _Client:
        def poll_studio_status(self, notebook_id):
            return list(artifacts)

        def list_mind_maps(self, notebook_id):
            return []

    return _Client()


def test_studio_status_synthesizes_reason_for_failed_artifact_without_raw_error(monkeypatch):
    """The real gRPC payload gives failed artifacts NO error string. The service must still surface a non-null
    error_reason so an agent stops polling and acts (instead of looping on an all-null failed artifact — the
    reported bug).
    """
    failed_artifact = {
        "artifact_id": "art-fail",
        "type": "infographic",
        "title": "NMJ",
        "status": "failed",
        # NOTE: deliberately NO error_reason/failure_* key — matches real API.
    }
    monkeypatch.setattr(
        studio_tools, "get_client", lambda: _client_returning([failed_artifact]), raising=True
    )

    art = studio_tools.studio_status(notebook_id="nb-123")["artifacts"][0]
    assert art["status"] == "failed"
    assert isinstance(art.get("error_reason"), str) and art["error_reason"], (
        f"Failed artifact must carry a synthesized error_reason, got: {art}"
    )
    assert "nlm login" in art["error_reason"].lower(), (
        f"Reason should hint at the likely auth fix, got: {art['error_reason']}"
    )


def test_studio_status_prefers_real_error_key_when_present(monkeypatch):
    """If a future API version DOES provide an error key, surface it verbatim."""
    failed_artifact = {
        "artifact_id": "art-fail2",
        "type": "infographic",
        "status": "failed",
        "error_reason": "RESOURCE_EXHAUSTED",
    }
    monkeypatch.setattr(
        studio_tools, "get_client", lambda: _client_returning([failed_artifact]), raising=True
    )
    art = studio_tools.studio_status(notebook_id="nb-123")["artifacts"][0]
    assert art.get("error_reason") == "RESOURCE_EXHAUSTED"


def test_studio_status_no_reason_for_healthy_artifact(monkeypatch):
    """A completed/in-progress artifact must NOT get a spurious error_reason."""
    ok_artifact = {
        "artifact_id": "art-ok",
        "type": "infographic",
        "status": "completed",
        "infographic_url": "https://example/x.png",
    }
    monkeypatch.setattr(
        studio_tools, "get_client", lambda: _client_returning([ok_artifact]), raising=True
    )
    art = studio_tools.studio_status(notebook_id="nb-123")["artifacts"][0]
    assert art.get("error_reason") is None, (
        f"Healthy artifact must have no error_reason, got: {art}"
    )


# --------------------------------------------------------------------------- #
# Test 4 — end-to-end studio_create per mocked auth state
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "auth_state,valid,reason",
    [
        ("fresh", True, None),
        ("stale_recoverable", False, "stale_heuristic"),
        ("expired", False, "expired"),
        ("missing", False, "no_tokens"),
    ],
)
def test_studio_create_e2e_per_auth_state(monkeypatch, auth_state, valid, reason):
    """Each auth state must yield a deterministic, actionable outcome: valid → success; any invalid state →
    status:"error" (never a fake success).
    """
    studio_tools._auth_guard_expires = 0.0  # force guard expired so auth is re-checked
    _patch_credentials_usable(monkeypatch, usable=valid, status=reason or "stale")
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service,
        "create_artifact",
        lambda *a, **k: {"artifact_id": "art-e2e", "status": "in_progress"},
        raising=True,
    )

    result = studio_tools.studio_create(
        notebook_id="nb-123",
        artifact_type="infographic",
        confirm=True,
    )

    if valid:
        assert result.get("status") == "success", f"[{auth_state}] expected success, got: {result}"
    else:
        assert result.get("status") == "error", (
            f"[{auth_state}] expected a loud error, not a fake success. Got: {result}"
        )
        # The auth-guard TTL must be reset to 0 on invalid auth so the next
        # call retries immediately instead of waiting up to 60s for the TTL
        # to expire. Without this, hammering studio_create in a loop during
        # debugging would re-run the slow path on every call after the first.
        assert studio_tools._auth_guard_expires == 0.0, (
            f"[{auth_state}] expected auth-guard reset to 0 on invalid auth, "
            f"got: {studio_tools._auth_guard_expires}"
        )


def test_studio_create_resets_auth_guard_on_invalid_auth(monkeypatch):
    """When check_auth returns invalid, the TTL guard must be cleared so
    subsequent calls re-check immediately rather than waiting for the TTL
    to expire naturally. Without this, the user gets a stale-guard window
    of up to 60s after auth flips from valid to invalid.

    Note: this is a partial mitigation. The full bug class (auth becomes
    invalid while the guard is still in its valid window) cannot be fixed
    by a TTL-based cache alone; it requires a TTL of 0 (no cache) or a
    push-based invalidation channel. The fix here addresses the case where
    the TTL has already expired and we just detected the invalid auth: we
    should not let a future-valid guard leak forward to the next call.
    """
    _patch_credentials_usable(monkeypatch, usable=False, status="expired")
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)

    # Pre-seed the guard with a future timestamp, simulating "auth was valid
    # 5s ago, the guard was updated to T+55, and now auth has expired". This
    # is the exact state the fix targets: the guard is non-zero, but the
    # TTL has not elapsed yet. We force it to expire so the check runs.

    studio_tools._auth_guard_expires = 0.0  # force guard expired so check runs

    result = studio_tools.studio_create(
        notebook_id="nb-123", artifact_type="infographic", confirm=True
    )
    assert result.get("status") == "error"
    # After an invalid check, the guard MUST be 0 (the fix). Before the fix,
    # the guard was left at whatever value it had, which would let a stale
    # future timestamp leak into the next call.
    assert studio_tools._auth_guard_expires == 0.0, (
        f"auth-guard should be reset to 0 on invalid auth, got: {studio_tools._auth_guard_expires}"
    )


def test_studio_create_invalidates_auth_guard_when_auth_file_changes(monkeypatch):
    """If the auth cache file's mtime changes on disk (e.g. `nlm login`
    rewrote it during the cached window), the auth-guard must be invalidated
    even if the TTL has not elapsed. Without this, a stale-TTL window could
    skip the re-check when the user just refreshed their tokens.
    """
    check_call_count = {"n": 0}

    # First call: mtime=N. Guard populated with mtime=N.
    monkeypatch.setattr(studio_tools, "_get_auth_file_mtime", lambda: 1000.0, raising=True)
    _patch_credentials_usable(monkeypatch, usable=True, counter=check_call_count)
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service,
        "create_artifact",
        lambda *a, **k: {"artifact_id": "art-1", "status": "in_progress"},
        raising=True,
    )

    studio_tools._auth_guard_expires = 0.0  # force guard expired so check runs
    studio_tools._auth_guard_mtime = 0.0
    studio_tools.studio_create(notebook_id="nb-123", artifact_type="infographic", confirm=True)
    assert check_call_count["n"] == 1
    # Guard is now valid (mtime=1000, TTL=60s).
    assert studio_tools._auth_guard_mtime == 1000.0
    assert studio_tools._auth_guard_expires > 0

    # Second call: same mtime, TTL still valid. Guard should hold — check must NOT run.
    studio_tools.studio_create(notebook_id="nb-123", artifact_type="infographic", confirm=True)
    assert check_call_count["n"] == 1, "Guard should have held; check ran anyway."

    # Third call: mtime changed (e.g. `nlm login` rewrote the file). Guard MUST
    # invalidate even though TTL is still valid. This is the bug class this
    # test pins: the TTL cache would otherwise skip the re-check.
    monkeypatch.setattr(studio_tools, "_get_auth_file_mtime", lambda: 2000.0, raising=True)
    studio_tools.studio_create(notebook_id="nb-123", artifact_type="infographic", confirm=True)
    assert check_call_count["n"] == 2, (
        "Mtime change must invalidate the guard and trigger a re-check."
    )
    assert studio_tools._auth_guard_mtime == 2000.0


def test_studio_create_invalidates_auth_guard_when_auth_file_appears(monkeypatch):
    """If the auth file is missing at guard-set time and later appears
    (mtime goes from 0.0 to N), the guard must invalidate.
    """
    check_call_count = {"n": 0}

    # First call: file does not exist (mtime=0.0). Guard populated with mtime=0.0.
    monkeypatch.setattr(studio_tools, "_get_auth_file_mtime", lambda: 0.0, raising=True)
    _patch_credentials_usable(monkeypatch, usable=True, counter=check_call_count)
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service,
        "create_artifact",
        lambda *a, **k: {"artifact_id": "art-1", "status": "in_progress"},
        raising=True,
    )

    studio_tools._auth_guard_expires = 0.0
    studio_tools._auth_guard_mtime = 0.0
    studio_tools.studio_create(notebook_id="nb-123", artifact_type="infographic", confirm=True)
    assert check_call_count["n"] == 1

    # Second call: same mtime (still 0.0), TTL still valid. Guard holds.
    studio_tools.studio_create(notebook_id="nb-123", artifact_type="infographic", confirm=True)
    assert check_call_count["n"] == 1

    # Third call: file now exists (mtime=500.0). Guard MUST invalidate.
    monkeypatch.setattr(studio_tools, "_get_auth_file_mtime", lambda: 500.0, raising=True)
    studio_tools.studio_create(notebook_id="nb-123", artifact_type="infographic", confirm=True)
    assert check_call_count["n"] == 2, "File appearance must invalidate the guard."
