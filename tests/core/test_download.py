#!/usr/bin/env python3
"""Tests for DownloadMixin."""

from unittest.mock import AsyncMock, patch

import pytest

from notebooklm_tools.core.base import BaseClient
from notebooklm_tools.core.download import DownloadMixin


class TestDownloadMixinImport:
    """Test that DownloadMixin can be imported correctly."""

    def test_download_mixin_import(self):
        """Test that DownloadMixin can be imported."""
        assert DownloadMixin is not None

    def test_download_mixin_inherits_base(self):
        """Test that DownloadMixin inherits from BaseClient."""
        assert issubclass(DownloadMixin, BaseClient)

    def test_download_mixin_has_binary_download_methods(self):
        """Test that DownloadMixin has binary download methods."""
        expected_methods = [
            "download_audio",
            "download_video",
            "download_infographic",
            "download_slide_deck",
        ]
        for method in expected_methods:
            assert hasattr(DownloadMixin, method), f"Missing method: {method}"

    def test_download_mixin_has_text_download_methods(self):
        """Test that DownloadMixin has text download methods."""
        expected_methods = [
            "download_report",
            "download_mind_map",
            "download_data_table",
        ]
        for method in expected_methods:
            assert hasattr(DownloadMixin, method), f"Missing method: {method}"

    def test_download_mixin_has_interactive_download_methods(self):
        """Test that DownloadMixin has interactive download methods."""
        expected_methods = [
            "download_quiz",
            "download_flashcards",
        ]
        for method in expected_methods:
            assert hasattr(DownloadMixin, method), f"Missing method: {method}"

    def test_download_mixin_has_helper_methods(self):
        """Test that DownloadMixin has helper methods."""
        expected_methods = [
            "_download_url",
            "_list_raw",
            "_extract_cell_text",
            "_parse_data_table",
            "_get_artifact_content",
            "_extract_app_data",
        ]
        for method in expected_methods:
            assert hasattr(DownloadMixin, method), f"Missing method: {method}"


class TestDownloadMixinMethods:
    """Test DownloadMixin method behavior."""

    def test_extract_cell_text_handles_none(self):
        """Test that _extract_cell_text handles None input."""
        result = DownloadMixin._extract_cell_text(None)
        assert result == ""

    def test_extract_cell_text_handles_string(self):
        """Test that _extract_cell_text handles string input."""
        result = DownloadMixin._extract_cell_text("  test value  ")
        assert result == "test value"

    def test_extract_cell_text_handles_integer(self):
        """Test that _extract_cell_text handles integer input (position marker)."""
        result = DownloadMixin._extract_cell_text(42)
        assert result == ""

    def test_extract_cell_text_handles_nested_list(self):
        """Test that _extract_cell_text handles nested list input."""
        result = DownloadMixin._extract_cell_text([1, "hello", [2, "world"]])
        assert "hello" in result
        assert "world" in result

    def test_format_quiz_markdown(self):
        """Test quiz markdown formatting."""
        questions = [
            {
                "question": "What is 2+2?",
                "answerOptions": [
                    {"text": "3", "isCorrect": False},
                    {"text": "4", "isCorrect": True},
                ],
                "hint": "Think simple",
            }
        ]
        result = DownloadMixin._format_quiz_markdown("Test Quiz", questions)
        assert "# Test Quiz" in result
        assert "## Question 1" in result
        assert "What is 2+2?" in result
        assert "[x] 4" in result
        assert "[ ] 3" in result
        assert "**Hint:** Think simple" in result

    def test_format_flashcards_markdown(self):
        """Test flashcard markdown formatting."""
        cards = [{"f": "Front text", "b": "Back text"}]
        result = DownloadMixin._format_flashcards_markdown("Test Deck", cards)
        assert "# Test Deck" in result
        assert "## Card 1" in result
        assert "**Front:** Front text" in result
        assert "**Back:** Back text" in result

    def test_is_audio_artifact_ready_accepts_verified_status_2_payload(self):
        mixin = DownloadMixin(cookies={"test": "cookie"}, csrf_token="test")
        artifact = [
            "art-1",
            "Audio",
            mixin.STUDIO_TYPE_AUDIO,
            [],
            2,
            None,
            [
                None,
                ["", 2, None, [["src-1"]], "en", True, 1],
                "https://example.com/thumb",
                "https://example.com/thumb-dv",
                None,
                [["https://example.com/audio.m4a", 1, "audio/mp4"]],
                [],
            ],
        ]

        assert mixin._is_audio_artifact_ready(artifact) is True

    @pytest.mark.asyncio
    async def test_download_audio_accepts_verified_status_2_payload(self):
        mixin = DownloadMixin(cookies={"test": "cookie"}, csrf_token="test")
        artifact = [
            "art-1",
            "Audio",
            mixin.STUDIO_TYPE_AUDIO,
            [],
            2,
            None,
            [
                None,
                ["", 2, None, [["src-1"]], "en", True, 1],
                "https://example.com/thumb",
                "https://example.com/thumb-dv",
                None,
                [["https://example.com/audio.m4a", 1, "audio/mp4"]],
                [],
            ],
        ]

        mixin._list_raw = lambda notebook_id: [artifact]
        mixin._download_url = AsyncMock(return_value="/tmp/audio.m4a")

        result = await mixin.download_audio("nb-1", "/tmp/audio.m4a")

        assert result == "/tmp/audio.m4a"
        mixin._download_url.assert_awaited_once_with(
            "https://example.com/audio.m4a",
            "/tmp/audio.m4a",
            None,
        )


class TestDownloadUrlCookies:
    """Cookie handling for cross-domain artifact downloads."""

    @pytest.mark.asyncio
    async def test_download_url_strips_osid_cookies(self, tmp_path):
        """OSID cookies must be removed before issuing the download request.

        OSID is scoped to notebooklm.google.com. If it leaks onto a download
        host such as lh3.googleusercontent.com, Google treats the request as
        an invalid session and redirects to ServiceLogin.
        """
        mixin = DownloadMixin(
            cookies=[
                {"name": "SID", "value": "sid-value", "domain": ".google.com", "path": "/"},
                {"name": "OSID", "value": "osid-value", "domain": ".google.com", "path": "/"},
                {
                    "name": "__Secure-OSID",
                    "value": "secure-osid-value",
                    "domain": ".google.com",
                    "path": "/",
                },
            ],
            csrf_token="token",
        )

        captured = {}

        class MockStreamResponse:
            headers = {
                "content-length": "4",
                "content-type": "application/octet-stream",
            }

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            def raise_for_status(self):
                return None

            async def aiter_bytes(self, chunk_size=8192):
                yield b"data"

        class MockAsyncClient:
            def __init__(self, *, cookies, headers, follow_redirects, timeout):
                captured["cookies"] = cookies

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            def stream(self, method, url):
                return MockStreamResponse()

        output = tmp_path / "out.bin"

        with patch("notebooklm_tools.core.download.httpx.AsyncClient", MockAsyncClient):
            result = await mixin._download_url(
                "https://lh3.googleusercontent.com/file", str(output)
            )

        assert result == str(output)
        assert output.read_bytes() == b"data"

        cookies = captured["cookies"]
        assert cookies.get("SID", domain=".google.com") == "sid-value"
        assert cookies.get("SID", domain=".googleusercontent.com") == "sid-value"
        for domain in (".google.com", ".googleusercontent.com"):
            assert cookies.get("OSID", domain=domain) is None
            assert cookies.get("__Secure-OSID", domain=domain) is None
