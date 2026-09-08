"""Regression tests for MCP debug log redaction.

Covers GHSA-jhrc-qgxv-3c2g: requests were sanitized but responses were
serialized whole, and the denylist was exact-match only.
"""

import json

import pytest

from notebooklm_tools.mcp.tools._utils import (
    _is_sensitive_key,
    _redact,
    _sanitize_params,
)


@pytest.mark.parametrize(
    "key",
    [
        "cookies",
        "csrf_token",
        "session_id",
        "request_body",
        "request_url",
        "access_token",
        "refresh_token",
        "api_key",
        "apiKey",
        "Authorization",
        "client_secret",
        "password",
        "bearer_token",
        "user_credentials",
    ],
)
def test_sensitive_keys_detected(key):
    assert _is_sensitive_key(key)


@pytest.mark.parametrize(
    "key",
    ["query", "title", "notebook_id", "author", "download_url", "artifact_type", "count"],
)
def test_ordinary_keys_survive(key):
    assert not _is_sensitive_key(key)


def test_top_level_request_params_redacted():
    out = _sanitize_params({"cookies": "SID=abc", "query": "hello"})
    assert out == {"cookies": "[REDACTED]", "query": "hello"}


def test_nested_response_redacted():
    payload = {
        "success": True,
        "auth": {"cookies": "SID=abc", "csrf_token": "at123"},
        "sources": [{"name": "a"}, {"name": "b", "access_token": "leaky"}],
    }
    out = _redact(payload)
    assert out["auth"]["cookies"] == "[REDACTED]"
    assert out["auth"]["csrf_token"] == "[REDACTED]"
    assert out["sources"][1]["access_token"] == "[REDACTED]"
    assert out["sources"][0]["name"] == "a"
    assert out["success"] is True


def test_no_secret_survives_serialization():
    payload = {"level1": {"level2": {"session_id": "s3cret-value"}}}
    assert "s3cret-value" not in json.dumps(_redact(payload), default=str)


def test_deep_nesting_is_bounded():
    node: dict = {}
    cursor = node
    for _ in range(30):
        cursor["next"] = {}
        cursor = cursor["next"]
    assert "[TRUNCATED]" in json.dumps(_redact(node), default=str)


def test_original_payload_not_mutated():
    payload = {"cookies": "SID=abc"}
    _redact(payload)
    assert payload["cookies"] == "SID=abc"


def test_non_dict_values_pass_through():
    assert _redact("plain") == "plain"
    assert _redact(42) == 42
    assert _redact(None) is None
    assert _redact([1, 2, 3]) == [1, 2, 3]
