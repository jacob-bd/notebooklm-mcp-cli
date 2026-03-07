"""Tests for services.studio module."""

import json

import pytest
from unittest.mock import MagicMock, patch

from notebooklm_tools.services.studio import (
    validate_artifact_type,
    resolve_code,
    create_artifact,
    get_studio_status,
    rename_artifact,
    delete_artifact,
    VALID_ARTIFACT_TYPES,
)
from notebooklm_tools.services.errors import ValidationError, ServiceError


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Source resolution
    client.get_notebook_sources_with_types.return_value = [
        {"id": "src-1", "title": "Source 1"},
        {"id": "src-2", "title": "Source 2"},
    ]
    # Standard creation result
    client.create_audio_overview.return_value = {"artifact_id": "art-1", "status": "in_progress"}
    client.create_video_overview.return_value = {"artifact_id": "art-2", "status": "in_progress"}
    client.create_infographic.return_value = {"artifact_id": "art-3", "status": "in_progress"}
    client.create_slide_deck.return_value = {"artifact_id": "art-4", "status": "in_progress"}
    client.create_report.return_value = {"artifact_id": "art-5", "status": "in_progress"}
    client.create_flashcards.return_value = {"artifact_id": "art-6", "status": "in_progress"}
    client.create_quiz.return_value = {"artifact_id": "art-7", "status": "in_progress"}
    client.create_data_table.return_value = {"artifact_id": "art-8", "status": "in_progress"}
    # Mind map
    client.generate_mind_map.return_value = {
        "mind_map_json": json.dumps({"name": "Root", "children": [{"name": "A"}, {"name": "B"}]}),
    }
    client.save_mind_map.return_value = {
        "mind_map_id": "mm-1",
        "title": "My Map",
        "mind_map_json": json.dumps({"name": "Root", "children": [{"name": "A"}, {"name": "B"}]}),
    }
    # Status
    client.poll_studio_status.return_value = [
        {"artifact_id": "a1", "type": "audio", "status": "completed"},
        {"artifact_id": "a2", "type": "report", "status": "in_progress"},
    ]
    client.list_mind_maps.return_value = [
        {"mind_map_id": "mm-1", "title": "Map 1"},
    ]
    # Rename/delete
    client.rename_studio_artifact.return_value = True
    client.delete_studio_artifact.return_value = True
    return client


class TestValidateArtifactType:
    """Test validate_artifact_type function."""

    @pytest.mark.parametrize("artifact_type", sorted(VALID_ARTIFACT_TYPES))
    def test_valid_types_pass(self, artifact_type):
        validate_artifact_type(artifact_type)  # should not raise

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError, match="Unknown artifact type"):
            validate_artifact_type("podcast")


class TestResolveCode:
    """Test resolve_code function."""

    def test_valid_code(self):
        mapper = MagicMock()
        mapper.get_code.return_value = 42
        assert resolve_code(mapper, "deep_dive", "audio format") == 42

    def test_invalid_code_raises(self):
        mapper = MagicMock()
        mapper.get_code.side_effect = ValueError("Unknown")
        mapper.names = ["a", "b"]
        with pytest.raises(ValidationError, match="Unknown audio format"):
            resolve_code(mapper, "bad", "audio format")


class TestCreateArtifact:
    """Test create_artifact function."""

    def test_create_audio(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "audio")
        assert result["artifact_type"] == "audio"
        assert result["artifact_id"] == "art-1"
        assert "generation started" in result["message"].lower()

    def test_create_video(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "video")
        assert result["artifact_type"] == "video"
        assert result["artifact_id"] == "art-2"

    def test_create_video_cinematic(self, mock_client):
        """Cinematic format resolves to code 3 and calls client correctly."""
        result = create_artifact(mock_client, "nb-1", "video", video_format="cinematic")
        assert result["artifact_type"] == "video"
        assert result["artifact_id"] == "art-2"
        # Verify format_code=3 (VIDEO_FORMAT_CINEMATIC) was passed
        call_kwargs = mock_client.create_video_overview.call_args
        assert call_kwargs[1]["format_code"] == 3

    def test_create_video_invalid_format(self, mock_client):
        """Invalid video format raises ValidationError."""
        with pytest.raises(ValidationError, match="Unknown video format"):
            create_artifact(mock_client, "nb-1", "video", video_format="invalid_format")

    def test_create_infographic(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "infographic")
        assert result["artifact_type"] == "infographic"
        assert result["artifact_id"] == "art-3"

    def test_create_slide_deck(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "slide_deck")
        assert result["artifact_type"] == "slide_deck"
        assert result["artifact_id"] == "art-4"

    def test_create_report(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "report")
        assert result["artifact_type"] == "report"
        assert result["artifact_id"] == "art-5"

    def test_create_flashcards(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "flashcards")
        assert result["artifact_type"] == "flashcards"
        assert result["artifact_id"] == "art-6"

    def test_create_quiz(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "quiz")
        assert result["artifact_type"] == "quiz"
        assert result["artifact_id"] == "art-7"

    def test_create_data_table(self, mock_client):
        result = create_artifact(
            mock_client, "nb-1", "data_table",
            description="Compare features",
        )
        assert result["artifact_type"] == "data_table"
        assert result["artifact_id"] == "art-8"

    def test_create_data_table_missing_description(self, mock_client):
        with pytest.raises(ValidationError, match="description is required"):
            create_artifact(mock_client, "nb-1", "data_table")

    def test_create_mind_map(self, mock_client):
        result = create_artifact(mock_client, "nb-1", "mind_map")
        assert result["artifact_type"] == "mind_map"
        assert result["artifact_id"] == "mm-1"
        assert result["root_name"] == "Root"
        assert result["children_count"] == 2

    def test_invalid_type(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown artifact type"):
            create_artifact(mock_client, "nb-1", "podcast")

    def test_uses_provided_source_ids(self, mock_client):
        create_artifact(mock_client, "nb-1", "report", source_ids=["s1"])
        mock_client.get_notebook_sources_with_types.assert_not_called()
        mock_client.create_report.assert_called_once()

    def test_fetches_source_ids_when_not_provided(self, mock_client):
        create_artifact(mock_client, "nb-1", "report")
        mock_client.get_notebook_sources_with_types.assert_called_once_with("nb-1")

    def test_no_sources_in_notebook_raises(self, mock_client):
        mock_client.get_notebook_sources_with_types.return_value = []
        with pytest.raises(ValidationError, match="No sources found"):
            create_artifact(mock_client, "nb-1", "report")

    def test_no_artifact_id_raises(self, mock_client):
        mock_client.create_report.return_value = {}
        with pytest.raises(ServiceError, match="rejected"):
            create_artifact(mock_client, "nb-1", "report")

    def test_api_error_wraps(self, mock_client):
        mock_client.create_report.side_effect = RuntimeError("boom")
        with pytest.raises(ServiceError, match="Failed to create"):
            create_artifact(mock_client, "nb-1", "report")

    def test_mind_map_gen_failure(self, mock_client):
        mock_client.generate_mind_map.return_value = {}
        with pytest.raises(ServiceError, match="Failed to generate"):
            create_artifact(mock_client, "nb-1", "mind_map")

    def test_mind_map_save_failure(self, mock_client):
        mock_client.save_mind_map.return_value = None
        with pytest.raises(ServiceError, match="Failed to save mind map"):
            create_artifact(mock_client, "nb-1", "mind_map")


class TestGetStudioStatus:
    """Test get_studio_status function."""

    def test_returns_combined_artifacts(self, mock_client):
        result = get_studio_status(mock_client, "nb-1")
        assert result["total"] == 3  # 2 studio + 1 mind map
        assert result["completed"] == 2  # 1 studio + 1 mind map
        assert result["in_progress"] == 1

    def test_mind_map_fetch_failure_ignored(self, mock_client):
        mock_client.list_mind_maps.side_effect = RuntimeError("fail")
        result = get_studio_status(mock_client, "nb-1")
        assert result["total"] == 2  # only studio artifacts

    def test_api_error(self, mock_client):
        mock_client.poll_studio_status.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to poll"):
            get_studio_status(mock_client, "nb-1")


class TestRenameArtifact:
    """Test rename_artifact function."""

    def test_success(self, mock_client):
        result = rename_artifact(mock_client, "art-1", "New Title")
        assert result["artifact_id"] == "art-1"
        assert result["new_title"] == "New Title"

    def test_missing_artifact_id(self, mock_client):
        with pytest.raises(ValidationError, match="artifact_id is required"):
            rename_artifact(mock_client, "", "Title")

    def test_missing_new_title(self, mock_client):
        with pytest.raises(ValidationError, match="new_title is required"):
            rename_artifact(mock_client, "art-1", "")

    def test_falsy_result(self, mock_client):
        mock_client.rename_studio_artifact.return_value = False
        with pytest.raises(ServiceError, match="Rename returned falsy"):
            rename_artifact(mock_client, "art-1", "Title")

    def test_api_error(self, mock_client):
        mock_client.rename_studio_artifact.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to rename"):
            rename_artifact(mock_client, "art-1", "Title")


class TestDeleteArtifact:
    """Test delete_artifact function."""

    def test_success(self, mock_client):
        delete_artifact(mock_client, "art-1", "nb-1")
        mock_client.delete_studio_artifact.assert_called_once_with("art-1", notebook_id="nb-1")

    def test_falsy_result(self, mock_client):
        mock_client.delete_studio_artifact.return_value = False
        with pytest.raises(ServiceError, match="Delete returned falsy"):
            delete_artifact(mock_client, "art-1", "nb-1")

    def test_api_error(self, mock_client):
        mock_client.delete_studio_artifact.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to delete"):
            delete_artifact(mock_client, "art-1", "nb-1")
