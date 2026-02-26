"""Tests for services.sources module."""

import pytest
from unittest.mock import MagicMock

from notebooklm_tools.services.sources import (
    validate_source_type,
    resolve_drive_mime_type,
    add_source,
    add_sources,
    list_drive_sources,
    sync_drive_sources,
    delete_source,
    delete_sources,
    describe_source,
    get_source_content,
    VALID_SOURCE_TYPES,
)
from notebooklm_tools.services.errors import ValidationError, ServiceError


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Add source methods
    client.add_url_source.return_value = {"id": "src-1", "title": "Example Page"}
    client.add_text_source.return_value = {"id": "src-2", "title": "My Text"}
    client.add_drive_source.return_value = {"id": "src-3", "title": "Drive Doc"}
    client.add_file.return_value = {"id": "src-4", "title": "doc.pdf"}
    # List/freshness methods
    client.get_notebook_sources_with_types.return_value = [
        {"id": "s1", "title": "Source 1", "source_type_name": "URL", "can_sync": False},
        {"id": "s2", "title": "Source 2", "source_type_name": "Drive", "can_sync": True, "drive_doc_id": "d1"},
    ]
    client.check_source_freshness.return_value = True
    # Sync/delete/describe/content
    client.sync_drive_source.return_value = True
    client.delete_source.return_value = True
    client.get_source_guide.return_value = {"summary": "Test summary", "keywords": ["a", "b"]}
    client.get_source_fulltext.return_value = {
        "content": "Hello world",
        "title": "Test Source",
        "type": "url",
    }
    return client


class TestValidateSourceType:
    """Test validate_source_type function."""

    @pytest.mark.parametrize("source_type", VALID_SOURCE_TYPES)
    def test_valid_types_pass(self, source_type):
        validate_source_type(source_type)  # should not raise

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError, match="Unknown source type"):
            validate_source_type("podcast")


class TestResolveDriveMimeType:
    """Test resolve_drive_mime_type function."""

    def test_doc(self):
        assert resolve_drive_mime_type("doc") == "application/vnd.google-apps.document"

    def test_slides(self):
        assert resolve_drive_mime_type("slides") == "application/vnd.google-apps.presentation"

    def test_sheets(self):
        assert resolve_drive_mime_type("sheets") == "application/vnd.google-apps.spreadsheet"

    def test_pdf(self):
        assert resolve_drive_mime_type("pdf") == "application/pdf"

    def test_unknown_defaults_to_doc(self):
        assert resolve_drive_mime_type("unknown") == "application/vnd.google-apps.document"


class TestAddSource:
    """Test add_source function."""

    def test_add_url_source(self, mock_client):
        result = add_source(mock_client, "nb-1", "url", url="https://example.com")
        assert result["source_type"] == "url"
        assert result["source_id"] == "src-1"
        assert result["title"] == "Example Page"

    def test_add_text_source(self, mock_client):
        result = add_source(mock_client, "nb-1", "text", text="some content")
        assert result["source_type"] == "text"
        assert result["source_id"] == "src-2"

    def test_add_text_source_default_title(self, mock_client):
        add_source(mock_client, "nb-1", "text", text="content")
        mock_client.add_text_source.assert_called_once_with(
            "nb-1", "content", "Pasted Text", wait=False, wait_timeout=120.0,
        )

    def test_add_drive_source(self, mock_client):
        result = add_source(mock_client, "nb-1", "drive", document_id="doc-123")
        assert result["source_type"] == "drive"
        assert result["source_id"] == "src-3"

    def test_add_drive_source_mime_type(self, mock_client):
        add_source(mock_client, "nb-1", "drive", document_id="d1", doc_type="slides")
        call_args = mock_client.add_drive_source.call_args
        assert call_args[0][3] == "application/vnd.google-apps.presentation"

    def test_add_file_source(self, mock_client):
        result = add_source(mock_client, "nb-1", "file", file_path="/tmp/doc.pdf")
        assert result["source_type"] == "file"
        assert result["source_id"] == "src-4"

    def test_invalid_source_type(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown source type"):
            add_source(mock_client, "nb-1", "podcast")

    def test_url_missing_raises(self, mock_client):
        with pytest.raises(ValidationError, match="url is required"):
            add_source(mock_client, "nb-1", "url")

    def test_text_missing_raises(self, mock_client):
        with pytest.raises(ValidationError, match="text is required"):
            add_source(mock_client, "nb-1", "text")

    def test_drive_missing_document_id_raises(self, mock_client):
        with pytest.raises(ValidationError, match="document_id is required"):
            add_source(mock_client, "nb-1", "drive")

    def test_file_missing_path_raises(self, mock_client):
        with pytest.raises(ValidationError, match="file_path is required"):
            add_source(mock_client, "nb-1", "file")

    def test_api_error_wraps_in_service_error(self, mock_client):
        mock_client.add_url_source.side_effect = RuntimeError("boom")
        with pytest.raises(ServiceError, match="Failed to add"):
            add_source(mock_client, "nb-1", "url", url="https://example.com")

    def test_no_id_returned_raises_service_error(self, mock_client):
        mock_client.add_url_source.return_value = {}
        with pytest.raises(ServiceError, match="no ID returned"):
            add_source(mock_client, "nb-1", "url", url="https://example.com")

    def test_wait_forwarded(self, mock_client):
        add_source(mock_client, "nb-1", "url", url="http://ex.com", wait=True, wait_timeout=60)
        mock_client.add_url_source.assert_called_once_with(
            "nb-1", "http://ex.com", wait=True, wait_timeout=60,
        )


class TestListDriveSources:
    """Test list_drive_sources function."""

    def test_returns_categorized_sources(self, mock_client):
        result = list_drive_sources(mock_client, "nb-1")
        assert result["drive_count"] == 1
        assert len(result["other_sources"]) == 1
        assert result["drive_sources"][0]["id"] == "s2"

    def test_stale_count(self, mock_client):
        mock_client.check_source_freshness.return_value = False
        result = list_drive_sources(mock_client, "nb-1")
        assert result["stale_count"] == 1
        assert result["drive_sources"][0]["stale"] is True

    def test_fresh_sources(self, mock_client):
        result = list_drive_sources(mock_client, "nb-1")
        assert result["stale_count"] == 0
        assert result["drive_sources"][0]["stale"] is False

    def test_api_error(self, mock_client):
        mock_client.get_notebook_sources_with_types.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to list"):
            list_drive_sources(mock_client, "nb-1")


class TestSyncDriveSources:
    """Test sync_drive_sources function."""

    def test_sync_success(self, mock_client):
        results = sync_drive_sources(mock_client, ["s1", "s2"])
        assert len(results) == 2
        assert all(r["synced"] for r in results)

    def test_sync_partial_failure(self, mock_client):
        mock_client.sync_drive_source.side_effect = [True, RuntimeError("fail")]
        results = sync_drive_sources(mock_client, ["s1", "s2"])
        assert results[0]["synced"] is True
        assert results[1]["synced"] is False
        assert results[1]["error"] == "fail"

    def test_empty_list_raises(self, mock_client):
        with pytest.raises(ValidationError, match="No source IDs"):
            sync_drive_sources(mock_client, [])


class TestDeleteSource:
    """Test delete_source function."""

    def test_success(self, mock_client):
        delete_source(mock_client, "src-1")
        mock_client.delete_source.assert_called_once_with("src-1")

    def test_falsy_result_raises(self, mock_client):
        mock_client.delete_source.return_value = False
        with pytest.raises(ServiceError, match="Delete returned falsy"):
            delete_source(mock_client, "src-1")

    def test_api_error(self, mock_client):
        mock_client.delete_source.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to delete"):
            delete_source(mock_client, "src-1")


class TestDescribeSource:
    """Test describe_source function."""

    def test_success(self, mock_client):
        result = describe_source(mock_client, "src-1")
        assert result["summary"] == "Test summary"
        assert result["keywords"] == ["a", "b"]

    def test_empty_result_raises(self, mock_client):
        mock_client.get_source_guide.return_value = None
        with pytest.raises(ServiceError, match="No description returned"):
            describe_source(mock_client, "src-1")


class TestGetSourceContent:
    """Test get_source_content function."""

    def test_success(self, mock_client):
        result = get_source_content(mock_client, "src-1")
        assert result["content"] == "Hello world"
        assert result["title"] == "Test Source"
        assert result["source_type"] == "url"
        assert result["char_count"] == 11

    def test_empty_result_raises(self, mock_client):
        mock_client.get_source_fulltext.return_value = None
        with pytest.raises(ServiceError, match="No content returned"):
            get_source_content(mock_client, "src-1")


class TestAddSources:
    """Test add_sources (bulk) function."""

    def test_batch_url_sources(self, mock_client):
        mock_client.add_url_sources.return_value = [
            {"id": "s1", "title": "Example"},
            {"id": "s2", "title": "Example Org"},
        ]
        result = add_sources(mock_client, "nb-1", [
            {"source_type": "url", "url": "https://example.com"},
            {"source_type": "url", "url": "https://example.org"},
        ])
        assert result["added_count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["source_id"] == "s1"
        assert result["results"][1]["source_id"] == "s2"
        # Should call batch method once, not individual add_url_source
        mock_client.add_url_sources.assert_called_once()
        mock_client.add_url_source.assert_not_called()

    def test_mixed_types_batches_urls(self, mock_client):
        """URL sources are batched; text sources fall back to individual calls."""
        mock_client.add_url_sources.return_value = [
            {"id": "s1", "title": "Example"},
        ]
        result = add_sources(mock_client, "nb-1", [
            {"source_type": "url", "url": "https://example.com"},
            {"source_type": "text", "text": "hello world"},
        ])
        assert result["added_count"] == 2
        mock_client.add_url_sources.assert_called_once()
        mock_client.add_text_source.assert_called_once()

    def test_empty_list_raises(self, mock_client):
        with pytest.raises(ValidationError, match="No sources provided"):
            add_sources(mock_client, "nb-1", [])

    def test_invalid_source_type_raises(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown source type"):
            add_sources(mock_client, "nb-1", [
                {"source_type": "podcast", "url": "https://example.com"},
            ])

    def test_url_missing_raises(self, mock_client):
        with pytest.raises(ValidationError, match="url is required"):
            add_sources(mock_client, "nb-1", [
                {"source_type": "url"},
            ])

    def test_batch_no_id_raises_service_error(self, mock_client):
        mock_client.add_url_sources.return_value = [{}]
        with pytest.raises(ServiceError, match="no ID returned"):
            add_sources(mock_client, "nb-1", [
                {"source_type": "url", "url": "https://example.com"},
            ])

    def test_batch_api_error_wraps(self, mock_client):
        mock_client.add_url_sources.side_effect = RuntimeError("boom")
        with pytest.raises(ServiceError, match="Failed to batch-add"):
            add_sources(mock_client, "nb-1", [
                {"source_type": "url", "url": "https://example.com"},
            ])

    def test_wait_forwarded(self, mock_client):
        mock_client.add_url_sources.return_value = [
            {"id": "s1", "title": "Example"},
        ]
        add_sources(mock_client, "nb-1", [
            {"source_type": "url", "url": "https://example.com"},
        ], wait=True, wait_timeout=60)
        mock_client.add_url_sources.assert_called_once_with(
            "nb-1", ["https://example.com"], wait=True, wait_timeout=60,
        )


class TestDeleteSources:
    """Test delete_sources (bulk) function."""

    def test_batch_delete(self, mock_client):
        mock_client.delete_sources.return_value = True
        delete_sources(mock_client, ["s1", "s2", "s3"])
        mock_client.delete_sources.assert_called_once_with(["s1", "s2", "s3"])

    def test_empty_list_raises(self, mock_client):
        with pytest.raises(ValidationError, match="No source IDs"):
            delete_sources(mock_client, [])

    def test_falsy_result_raises(self, mock_client):
        mock_client.delete_sources.return_value = False
        with pytest.raises(ServiceError, match="Bulk delete returned falsy"):
            delete_sources(mock_client, ["s1"])

    def test_api_error(self, mock_client):
        mock_client.delete_sources.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to delete"):
            delete_sources(mock_client, ["s1"])
