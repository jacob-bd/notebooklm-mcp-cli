"""Tests for services.downloads module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from notebooklm_tools.services.downloads import (
    VALID_ARTIFACT_TYPES,
    VALID_OUTPUT_FORMATS,
    download_async,
    download_sync,
    get_default_extension,
    validate_artifact_type,
    validate_output_format,
)
from notebooklm_tools.services.errors import ServiceError, ValidationError


@pytest.fixture(autouse=True)
def _sandbox_to_tmp(monkeypatch):
    """Set download sandbox to /tmp so test paths pass through unchanged."""
    monkeypatch.setenv("NOTEBOOKLM_DOWNLOAD_DIR", "/tmp")


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Set up async methods
    client.download_audio = AsyncMock(return_value="/tmp/audio.m4a")
    client.download_video = AsyncMock(return_value="/tmp/video.mp4")
    client.download_slide_deck = AsyncMock(return_value="/tmp/slides.pdf")
    client.download_infographic = AsyncMock(return_value="/tmp/infographic.png")
    client.download_quiz = AsyncMock(return_value="/tmp/quiz.json")
    client.download_flashcards = AsyncMock(return_value="/tmp/flashcards.json")
    # Sync methods
    client.download_report.return_value = "/tmp/report.md"
    client.download_mind_map.return_value = "/tmp/mindmap.json"
    client.download_data_table.return_value = "/tmp/table.csv"
    return client


class TestValidateArtifactType:
    """Test validate_artifact_type function."""

    @pytest.mark.parametrize("artifact_type", VALID_ARTIFACT_TYPES)
    def test_valid_types_pass(self, artifact_type):
        validate_artifact_type(artifact_type)  # should not raise

    def test_invalid_type_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Unknown artifact type"):
            validate_artifact_type("podcast")


class TestValidateOutputFormat:
    """Test validate_output_format function."""

    @pytest.mark.parametrize("fmt", VALID_OUTPUT_FORMATS)
    def test_valid_formats_pass(self, fmt):
        validate_output_format(fmt)  # should not raise

    def test_invalid_format_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Invalid output format"):
            validate_output_format("pdf")


class TestGetDefaultExtension:
    """Test get_default_extension function."""

    def test_audio_extension(self):
        assert get_default_extension("audio") == "m4a"

    def test_report_extension(self):
        assert get_default_extension("report") == "md"

    def test_quiz_default_json(self):
        assert get_default_extension("quiz") == "json"

    def test_quiz_markdown(self):
        assert get_default_extension("quiz", "markdown") == "md"

    def test_quiz_html(self):
        assert get_default_extension("quiz", "html") == "html"

    def test_flashcards_markdown(self):
        assert get_default_extension("flashcards", "markdown") == "md"


class TestDownloadSync:
    """Test download_sync for non-streaming artifacts."""

    def test_download_report(self, mock_client):
        result = download_sync(mock_client, "nb-1", "report", "/tmp/report.md")
        assert result["artifact_type"] == "report"
        assert result["path"] == "/tmp/report.md"

    def test_download_mind_map(self, mock_client):
        result = download_sync(mock_client, "nb-1", "mind_map", "/tmp/mm.json")
        assert result["path"] == "/tmp/mindmap.json"

    def test_download_data_table(self, mock_client):
        result = download_sync(mock_client, "nb-1", "data_table", "/tmp/t.csv")
        assert result["path"] == "/tmp/table.csv"

    def test_invalid_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown"):
            download_sync(mock_client, "nb-1", "podcast", "/tmp/out")

    def test_streaming_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="requires async"):
            download_sync(mock_client, "nb-1", "audio", "/tmp/out")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.download_report.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to download"):
            download_sync(mock_client, "nb-1", "report", "/tmp/out")

    def test_falsy_path_raises_service_error(self, mock_client):
        mock_client.download_report.return_value = None
        with pytest.raises(ServiceError, match="returned no path"):
            download_sync(mock_client, "nb-1", "report", "/tmp/out")


class TestDownloadAsync:
    """Test download_async for streaming artifacts."""

    @pytest.mark.asyncio
    async def test_download_audio(self, mock_client):
        result = await download_async(mock_client, "nb-1", "audio", "/tmp/a.m4a")
        assert result["artifact_type"] == "audio"
        assert result["path"] == "/tmp/audio.m4a"

    @pytest.mark.asyncio
    async def test_download_video(self, mock_client):
        result = await download_async(mock_client, "nb-1", "video", "/tmp/v.mp4")
        assert result["path"] == "/tmp/video.mp4"

    @pytest.mark.asyncio
    async def test_download_slide_deck(self, mock_client):
        result = await download_async(mock_client, "nb-1", "slide_deck", "/tmp/s.pdf")
        assert result["path"] == "/tmp/slides.pdf"

    @pytest.mark.asyncio
    async def test_download_infographic(self, mock_client):
        result = await download_async(mock_client, "nb-1", "infographic", "/tmp/i.png")
        assert result["path"] == "/tmp/infographic.png"

    @pytest.mark.asyncio
    async def test_download_quiz_json(self, mock_client):
        result = await download_async(
            mock_client,
            "nb-1",
            "quiz",
            "/tmp/q.json",
            output_format="json",
        )
        assert result["path"] == "/tmp/quiz.json"

    @pytest.mark.asyncio
    async def test_download_flashcards_html(self, mock_client):
        result = await download_async(
            mock_client,
            "nb-1",
            "flashcards",
            "/tmp/f.html",
            output_format="html",
        )
        assert result["path"] == "/tmp/flashcards.json"

    @pytest.mark.asyncio
    async def test_invalid_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown"):
            await download_async(mock_client, "nb-1", "podcast", "/tmp/out")

    @pytest.mark.asyncio
    async def test_invalid_format_for_quiz_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid output format"):
            await download_async(
                mock_client,
                "nb-1",
                "quiz",
                "/tmp/out",
                output_format="pdf",
            )

    @pytest.mark.asyncio
    async def test_api_error_raises_service_error(self, mock_client):
        mock_client.download_audio = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(ServiceError, match="Failed to download"):
            await download_async(mock_client, "nb-1", "audio", "/tmp/out")

    @pytest.mark.asyncio
    async def test_falsy_path_raises_service_error(self, mock_client):
        mock_client.download_audio = AsyncMock(return_value=None)
        with pytest.raises(ServiceError, match="returned no path"):
            await download_async(mock_client, "nb-1", "audio", "/tmp/out")

    @pytest.mark.asyncio
    async def test_progress_callback_passed_through(self, mock_client):
        cb = MagicMock()
        await download_async(
            mock_client,
            "nb-1",
            "audio",
            "/tmp/a.m4a",
            progress_callback=cb,
        )
        # Verify the callback was passed to the client method
        mock_client.download_audio.assert_called_once_with(
            "nb-1",
            "/tmp/a.m4a",
            None,
            progress_callback=cb,
        )

    @pytest.mark.asyncio
    async def test_download_report_via_async(self, mock_client):
        """Issue #107: report must be downloadable via download_async."""
        result = await download_async(mock_client, "nb-1", "report", "/tmp/r.md")
        assert result["artifact_type"] == "report"
        assert result["path"] == "/tmp/report.md"
        mock_client.download_report.assert_called_once_with("nb-1", "/tmp/r.md", None)

    @pytest.mark.asyncio
    async def test_download_mind_map_via_async(self, mock_client):
        """Issue #107: mind_map must be downloadable via download_async."""
        result = await download_async(mock_client, "nb-1", "mind_map", "/tmp/mm.json")
        assert result["artifact_type"] == "mind_map"
        assert result["path"] == "/tmp/mindmap.json"
        mock_client.download_mind_map.assert_called_once_with("nb-1", "/tmp/mm.json", None)

    @pytest.mark.asyncio
    async def test_download_data_table_via_async(self, mock_client):
        """Issue #107: data_table must be downloadable via download_async."""
        result = await download_async(mock_client, "nb-1", "data_table", "/tmp/dt.csv")
        assert result["artifact_type"] == "data_table"
        assert result["path"] == "/tmp/table.csv"
        mock_client.download_data_table.assert_called_once_with("nb-1", "/tmp/dt.csv", None)
