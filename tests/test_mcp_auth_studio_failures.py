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


# --------------------------------------------------------------------------- #
# Helpers / fakes
# --------------------------------------------------------------------------- #
def _auth_result(valid, reason=None):
    """Build a real AuthCheckResult so we exercise the production type."""
    return core_auth.AuthCheckResult(valid=valid, reason=reason, live=True, profile="default")


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
    monkeypatch.setattr(
        auth_tools, "get_client", lambda: _FakeClient(), raising=True
    )
    monkeypatch.setattr(auth_tools, "reset_client", lambda: None, raising=True)
    monkeypatch.setattr(
        core_auth, "load_cached_tokens",
        lambda: core_auth.AuthTokens(cookies={"SID": "x"}, extracted_at=0.0),
        raising=True,
    )
    # ...but a live check reports them expired.
    monkeypatch.setattr(core_auth, "check_auth", lambda **kw: _auth_result(False, "expired"), raising=True)
    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)

    result = auth_tools.refresh_auth()

    assert result.get("status") != "success", (
        "refresh_auth lied: returned success while tokens are expired. "
        f"Got: {result}"
    )
    # And it should point the user at the real fix.
    blob = (str(result.get("error", "")) + str(result.get("message", ""))).lower()
    assert "nlm login" in blob, f"Expected actionable 'nlm login' guidance, got: {result}"


def test_refresh_auth_reports_success_when_tokens_are_valid(monkeypatch):
    """The happy path must still work: valid tokens on disk → success."""
    monkeypatch.setattr(auth_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(auth_tools, "reset_client", lambda: None, raising=True)
    monkeypatch.setattr(
        core_auth, "load_cached_tokens",
        lambda: core_auth.AuthTokens(cookies={"SID": "x"}, extracted_at=0.0),
        raising=True,
    )
    monkeypatch.setattr(core_auth, "check_auth", lambda **kw: _auth_result(True), raising=True)
    monkeypatch.delenv("NOTEBOOKLM_COOKIES", raising=False)

    result = auth_tools.refresh_auth()
    assert result.get("status") == "success", f"Valid tokens should refresh OK, got: {result}"


# --------------------------------------------------------------------------- #
# Test 2 — studio_create pre-flight auth check
# --------------------------------------------------------------------------- #
def test_studio_create_fails_loudly_on_stale_auth(monkeypatch):
    """When auth is stale/expired, studio_create() must return status:"error" BEFORE firing a doomed generation request
    — not status:"success" with an artifact_id that immediately fails.
    """
    monkeypatch.setattr(studio_tools, "_check_studio_auth", lambda: _auth_result(False, "expired"), raising=False)
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
    monkeypatch.setattr(studio_tools, "_check_studio_auth", lambda: _auth_result(True), raising=False)
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service, "create_artifact",
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
    assert art.get("error_reason") is None, f"Healthy artifact must have no error_reason, got: {art}"


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
    monkeypatch.setattr(studio_tools, "_check_studio_auth", lambda: _auth_result(valid, reason), raising=False)
    monkeypatch.setattr(studio_tools, "get_client", lambda: _FakeClient(), raising=True)
    monkeypatch.setattr(
        studio_tools.studio_service, "create_artifact",
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
