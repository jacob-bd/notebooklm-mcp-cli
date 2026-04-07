"""Tests for file upload functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from notebooklm_tools.core.exceptions import FileUploadError, FileValidationError


class TestFileValidation:
    """Test file validation before upload."""

    def test_nonexistent_file_raises_error(self):
        """Test that non-existent file raises FileValidationError."""
        from notebooklm_tools.core.sources import SourceMixin

        # Create a mock client with minimal setup
        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {}
        client.csrf_token = "test"
        client._session_id = "test"
        client._client = None

        with pytest.raises(FileValidationError, match="File not found"):
            client.add_file("test-notebook-id", "/nonexistent/file.pdf")

    def test_empty_file_raises_error(self):
        """Test that empty file raises FileValidationError."""
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {}
        client.csrf_token = "test"
        client._session_id = "test"
        client._client = None

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(FileValidationError, match="empty"):
                client.add_file("test-notebook-id", temp_path)
        finally:
            Path(temp_path).unlink()

    def test_directory_raises_error(self):
        """Test that directory path raises FileValidationError."""
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {}
        client.csrf_token = "test"
        client._session_id = "test"
        client._client = None

        with tempfile.TemporaryDirectory() as tmpdir:  # noqa: SIM117
            with pytest.raises(FileValidationError, match="Not a regular file"):
                client.add_file("test-notebook-id", tmpdir)

    def test_unsupported_file_type_raises_error(self):
        """Test that unsupported file types raise FileValidationError."""
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {}
        client.csrf_token = "test"
        client._session_id = "test"
        client._client = None

        # Create a JSON file (unsupported type)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"test": "data"}')
            temp_path = f.name

        try:
            with pytest.raises(FileValidationError, match="Unsupported file type: .json"):
                client.add_file("test-notebook-id", temp_path)
        finally:
            Path(temp_path).unlink()


class TestFileUploadProtocol:
    """Test the 3-step upload protocol."""

    def test_register_file_source_success(self):
        """Test successful file registration (step 1)."""
        from notebooklm_tools.core.api_profile import APIProfile
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {"test": "cookie"}
        client.csrf_token = "test-csrf"
        client._session_id = "test-session"
        client._client = None
        client._profile = APIProfile()

        # Mock the HTTP client and response
        mock_response = Mock()
        mock_response.text = ')]}\'\n100\n[["wrb.fr","o4cbdc","[[[[\\"source-id-123\\"]]]]",null,null,null,"generic"]]'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_http_client = Mock()
        mock_http_client.post = Mock(return_value=mock_response)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            source_id = client._register_file_source("notebook-123", "test.pdf")

        assert source_id == "source-id-123"
        mock_http_client.post.assert_called_once()

    def test_register_file_source_failure(self):
        """Test file registration failure."""
        from notebooklm_tools.core.api_profile import APIProfile
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {"test": "cookie"}
        client.csrf_token = "test-csrf"
        client._session_id = "test-session"
        client._client = None
        client._profile = APIProfile()

        # Mock response with no source ID
        mock_response = Mock()
        mock_response.text = ')]}\'\n100\n[["wrb.fr","o4cbdc","null",null,null,null,"generic"]]'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_http_client = Mock()
        mock_http_client.post = Mock(return_value=mock_response)

        with patch.object(client, "_get_client", return_value=mock_http_client):  # noqa: SIM117
            with pytest.raises(FileUploadError, match="Failed to get SOURCE_ID"):
                client._register_file_source("notebook-123", "test.pdf")

    def test_start_resumable_upload_success(self):
        """Test starting resumable upload session (step 2)."""
        from notebooklm_tools.core.api_profile import APIProfile
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {"test": "cookie"}
        client.csrf_token = "test-csrf"
        client._session_id = "test-session"
        client._client = None
        client._profile = APIProfile()
        client.UPLOAD_URL = "https://notebooklm.google.com/upload/_/"

        # Mock response with upload URL
        mock_response = Mock()
        mock_response.headers = {"x-goog-upload-url": "https://upload.url/session123"}
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.object(client, "_get_httpx_cookies", return_value=httpx.Cookies()):
                upload_url = client._start_resumable_upload(
                    "notebook-123", "test.pdf", 1024, "source-id-123"
                )

        assert upload_url == "https://upload.url/session123"

    def test_start_resumable_upload_no_url(self):
        """Test upload session start without upload URL in response."""
        from notebooklm_tools.core.api_profile import APIProfile
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {"test": "cookie"}
        client.csrf_token = "test-csrf"
        client._session_id = "test-session"
        client._client = None
        client._profile = APIProfile()
        client.UPLOAD_URL = "https://notebooklm.google.com/upload/_/"

        # Mock response without upload URL
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.object(client, "_get_httpx_cookies", return_value=httpx.Cookies()):  # noqa: SIM117
                with pytest.raises(FileUploadError, match="Failed to get upload URL"):
                    client._start_resumable_upload(
                        "notebook-123", "test.pdf", 1024, "source-id-123"
                    )

    def test_upload_file_streaming_success(self):
        """Test streaming file upload (step 3)."""
        from notebooklm_tools.core.api_profile import APIProfile
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {"test": "cookie"}
        client.csrf_token = "test-csrf"
        client._session_id = "test-session"
        client._client = None
        client._profile = APIProfile()

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content for upload")
            temp_path = Path(f.name)

        try:
            # Mock successful upload
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()

            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client.__enter__ = Mock(return_value=mock_client)
                mock_client.__exit__ = Mock(return_value=False)
                mock_client.post = Mock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                with patch.object(client, "_get_httpx_cookies", return_value=httpx.Cookies()):
                    client._upload_file_streaming("https://upload.url/session123", temp_path)

            # Verify post was called
            mock_client.post.assert_called_once()
        finally:
            temp_path.unlink()


class TestAddFileIntegration:
    """Test the full add_file method integration."""

    def test_add_file_orchestrates_three_steps(self):
        """Test that add_file correctly orchestrates all three steps."""
        from notebooklm_tools.core.sources import SourceMixin

        client = SourceMixin.__new__(SourceMixin)
        client.cookies = {"test": "cookie"}
        client.csrf_token = "test-csrf"
        client._session_id = "test-session"
        client._client = None

        # Create a test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            # Mock all three steps
            with (
                patch.object(
                    client, "_register_file_source", return_value="source-id-123"
                ) as mock_register,
                patch.object(
                    client, "_start_resumable_upload", return_value="https://upload.url/session"
                ) as mock_start,
                patch.object(client, "_upload_file_streaming") as mock_upload,
            ):
                result = client.add_file("notebook-123", temp_path)

            # Verify all three steps were called
            mock_register.assert_called_once_with("notebook-123", temp_path.name)
            mock_start.assert_called_once()
            mock_upload.assert_called_once_with("https://upload.url/session", temp_path)

            # Verify result
            assert result["id"] == "source-id-123"
            assert result["title"] == temp_path.name
        finally:
            temp_path.unlink()


@pytest.mark.e2e
class TestFileUploadE2E:
    """E2E tests for file upload - requires NOTEBOOKLM_E2E=1."""

    def test_upload_text_file(self, temp_notebook):
        """Test uploading a text file (requires real authentication)."""
        from notebooklm_tools.core.auth import load_cached_tokens
        from notebooklm_tools.core.client import NotebookLMClient

        # Load real auth
        tokens = load_cached_tokens()
        if not tokens:
            pytest.skip("No authentication tokens available")

        client = NotebookLMClient(
            cookies=tokens.cookies, csrf_token=tokens.csrf_token, session_id=tokens.session_id
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content for NotebookLM upload.")
            temp_path = f.name

        try:
            result = client.add_file(temp_notebook.id, temp_path)
            assert result["id"] is not None
            assert result["title"].endswith(".txt")
        finally:
            Path(temp_path).unlink()


@pytest.fixture
def temp_notebook():
    """Create a temporary notebook for E2E tests."""
    from notebooklm_tools.core.auth import load_cached_tokens
    from notebooklm_tools.core.client import NotebookLMClient

    # Load real auth
    tokens = load_cached_tokens()
    if not tokens:
        pytest.skip("No authentication tokens available")

    client = NotebookLMClient(
        cookies=tokens.cookies, csrf_token=tokens.csrf_token, session_id=tokens.session_id
    )
    notebook = client.create_notebook(title="Test Upload Notebook")

    yield notebook

    # Cleanup
    try:  # noqa: SIM105
        client.delete_notebook(notebook.id)
    except Exception:
        pass  # Ignore cleanup errors
