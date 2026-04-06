"""Tests for dual RPC fallback in URL source addition (issue #121).

These tests exercise the core layer's add_url_source and add_url_sources
methods to verify the try-then-cache fallback between the legacy izAoDd
(v1) and new ozz5Z (v2) RPC endpoints.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from notebooklm_tools.core.errors import RPCError
from notebooklm_tools.core.sources import SourceMixin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOTEBOOK_ID = "test-notebook-123"
TEST_URL = "https://example.com/page"
YOUTUBE_URL = "https://www.youtube.com/watch?v=abc123"

# Simulated RPC response matching what both v1 and v2 return.
# Structure: [ [  [id_composite, title, ...], ...  ] ]
# where id_composite = ["source-id"]
MOCK_SOURCE_RESPONSE = [[[["src-id-001"], "Example Page", None, None]]]


def _make_client() -> SourceMixin:
    """Create a minimal SourceMixin with mocked internals.

    We patch __init__ entirely because BaseClient.__init__ requires
    real cookies / CSRF setup that we don't need for unit tests.
    """
    with patch.object(SourceMixin, "__init__", lambda self: None):
        client = SourceMixin()
    client._source_rpc_version = None
    client._call_rpc = MagicMock(return_value=MOCK_SOURCE_RESPONSE)
    return client


def _rpc_error_code_3(message: str = "INVALID_ARGUMENT") -> RPCError:
    """Create an RPCError with error_code=3 (the trigger for fallback)."""
    return RPCError(message=message, error_code=3)


# ===========================================================================
# Single URL: add_url_source
# ===========================================================================


class TestAddUrlSourceFallback:
    """Test dual RPC fallback for single URL addition."""

    def test_v1_success_no_fallback(self):
        """When v1 (izAoDd) works, v2 should never be called."""
        client = _make_client()

        result = client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert result == {"id": "src-id-001", "title": "Example Page"}
        assert client._source_rpc_version == "v1"
        # Should have called _call_rpc exactly once (v1)
        client._call_rpc.assert_called_once()
        call_args = client._call_rpc.call_args
        assert call_args[0][0] == client.RPC_ADD_SOURCE  # izAoDd

    def test_v1_fails_code3_v2_succeeds(self):
        """When v1 returns INVALID_ARGUMENT (code 3), should fallback to v2."""
        client = _make_client()
        # First call (v1) raises RPCError code 3, second call (v2) succeeds
        client._call_rpc.side_effect = [
            _rpc_error_code_3(),
            MOCK_SOURCE_RESPONSE,
        ]

        result = client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert result == {"id": "src-id-001", "title": "Example Page"}
        assert client._source_rpc_version == "v2"
        assert client._call_rpc.call_count == 2
        # First call was v1, second was v2
        first_call_rpc = client._call_rpc.call_args_list[0][0][0]
        second_call_rpc = client._call_rpc.call_args_list[1][0][0]
        assert first_call_rpc == client.RPC_ADD_SOURCE
        assert second_call_rpc == client.RPC_ADD_SOURCE_V2

    def test_cached_v2_skips_v1(self):
        """After caching v2, subsequent calls go straight to ozz5Z."""
        client = _make_client()
        client._source_rpc_version = "v2"

        result = client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert result == {"id": "src-id-001", "title": "Example Page"}
        client._call_rpc.assert_called_once()
        assert client._call_rpc.call_args[0][0] == client.RPC_ADD_SOURCE_V2

    def test_cached_v1_skips_detection(self):
        """After caching v1, subsequent calls go straight to izAoDd."""
        client = _make_client()
        client._source_rpc_version = "v1"

        result = client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert result == {"id": "src-id-001", "title": "Example Page"}
        client._call_rpc.assert_called_once()
        assert client._call_rpc.call_args[0][0] == client.RPC_ADD_SOURCE

    def test_both_rpcs_fail_raises_v2_error(self):
        """When both v1 and v2 fail, the v2 error should propagate."""
        client = _make_client()
        v2_error = RPCError(message="INTERNAL_ERROR", error_code=13)
        client._call_rpc.side_effect = [
            _rpc_error_code_3(),
            v2_error,
        ]

        with pytest.raises(RPCError) as exc_info:
            client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert exc_info.value.error_code == 13

    def test_v1_non_code3_error_not_caught(self):
        """RPCError with code != 3 should propagate immediately, no fallback."""
        client = _make_client()
        client._call_rpc.side_effect = RPCError(message="PERMISSION_DENIED", error_code=7)

        with pytest.raises(RPCError) as exc_info:
            client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert exc_info.value.error_code == 7
        # Only one call — no fallback attempt
        client._call_rpc.assert_called_once()

    def test_timeout_returns_status_dict(self):
        """httpx.TimeoutException should return a timeout status, not raise."""
        client = _make_client()
        client._call_rpc.side_effect = httpx.TimeoutException("timed out")

        result = client.add_url_source(NOTEBOOK_ID, TEST_URL)

        assert result["status"] == "timeout"

    def test_v2_payload_structure(self):
        """Verify the v2 payload matches the captured format from issue #121."""
        client = _make_client()
        client._source_rpc_version = "v2"

        client.add_url_source(NOTEBOOK_ID, TEST_URL)

        call_args = client._call_rpc.call_args
        params = call_args[0][1]  # Second positional arg is params
        # Structure: [[source_data]]
        assert len(params) == 1
        source_data = params[0][0]
        # [None, url, 627]
        assert source_data[0] == [None, TEST_URL, 627]
        # Ninth element contains [None, None, 1]
        assert source_data[1][9] == [None, None, 1]
        assert source_data[2] == 1

    def test_v2_youtube_no_distinction(self):
        """V2 uses the same structure for YouTube — no special position."""
        client = _make_client()
        client._source_rpc_version = "v2"

        client.add_url_source(NOTEBOOK_ID, YOUTUBE_URL)

        call_args = client._call_rpc.call_args
        params = call_args[0][1]
        source_data = params[0][0]
        assert source_data[0] == [None, YOUTUBE_URL, 627]


# ===========================================================================
# Bulk URL: add_url_sources
# ===========================================================================


class TestAddUrlSourcesBulkFallback:
    """Test dual RPC fallback for bulk URL addition."""

    def test_v1_success_no_fallback(self):
        """Bulk v1 path — no fallback needed."""
        client = _make_client()
        urls = [TEST_URL, "https://example.org"]
        client._call_rpc.return_value = [
            [
                [["s1"], "Page 1"],
                [["s2"], "Page 2"],
            ]
        ]

        result = client.add_url_sources(NOTEBOOK_ID, urls)

        assert len(result) == 2
        assert client._source_rpc_version == "v1"
        client._call_rpc.assert_called_once()
        assert client._call_rpc.call_args[0][0] == client.RPC_ADD_SOURCE

    def test_v1_fails_v2_succeeds_bulk(self):
        """Bulk fallback: v1 fails with code 3, v2 succeeds."""
        client = _make_client()
        urls = [TEST_URL]
        client._call_rpc.side_effect = [
            _rpc_error_code_3(),
            MOCK_SOURCE_RESPONSE,
        ]

        result = client.add_url_sources(NOTEBOOK_ID, urls)

        assert len(result) == 1
        assert result[0]["id"] == "src-id-001"
        assert client._source_rpc_version == "v2"

    def test_cached_v2_skips_v1_bulk(self):
        """Bulk with cached v2 skips detection."""
        client = _make_client()
        client._source_rpc_version = "v2"
        urls = [TEST_URL]

        client.add_url_sources(NOTEBOOK_ID, urls)

        client._call_rpc.assert_called_once()
        assert client._call_rpc.call_args[0][0] == client.RPC_ADD_SOURCE_V2

    def test_timeout_bulk(self):
        """Bulk timeout returns a list with timeout status."""
        client = _make_client()
        client._call_rpc.side_effect = httpx.TimeoutException("timed out")

        result = client.add_url_sources(NOTEBOOK_ID, [TEST_URL])

        assert len(result) == 1
        assert result[0]["status"] == "timeout"


# ===========================================================================
# Parse helpers
# ===========================================================================


class TestParseSourceResult:
    """Test the _parse_source_result static method."""

    def test_valid_result(self):
        result = SourceMixin._parse_source_result(MOCK_SOURCE_RESPONSE)
        assert result == {"id": "src-id-001", "title": "Example Page"}

    def test_empty_result(self):
        assert SourceMixin._parse_source_result([]) is None

    def test_none_result(self):
        assert SourceMixin._parse_source_result(None) is None

    def test_malformed_result_none_id(self):
        # source_data[0] is None → source_id is None
        assert SourceMixin._parse_source_result([[None, "title"]]) is None


class TestParseSourceResults:
    """Test the _parse_source_results static method."""

    def test_multiple_sources(self):
        result = SourceMixin._parse_source_results(
            [
                [
                    [["s1"], "Title 1"],
                    [["s2"], "Title 2"],
                ]
            ]
        )
        assert len(result) == 2
        assert result[0] == {"id": "s1", "title": "Title 1"}
        assert result[1] == {"id": "s2", "title": "Title 2"}

    def test_empty(self):
        assert SourceMixin._parse_source_results([]) == []
