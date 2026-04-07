"""Tests for MCP file upload functionality via consolidated source_add."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestMCPSourceAddFile:
    """Test file upload via the consolidated source_add MCP tool."""

    def test_source_add_file_exists(self):
        """Test that source_add tool with file type is available."""
        from notebooklm_tools.mcp.tools import sources

        # Check if source_add exists and supports file type
        assert hasattr(sources, "source_add")

    def test_source_add_file_calls_client(self):
        """Test that source_add file type calls client.add_file correctly."""
        from notebooklm_tools.mcp.tools import _utils, sources

        # Create a test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            # Mock the client
            mock_client = MagicMock()
            mock_client.add_file.return_value = {"id": "test-source-id", "title": "test.txt"}

            # Reset and patch get_client in sources module where it's imported
            _utils.reset_client()
            with patch("notebooklm_tools.mcp.tools.sources.get_client", return_value=mock_client):
                result = sources.source_add(
                    notebook_id="test-notebook-123", source_type="file", file_path=temp_path
                )

            # Verify client.add_file was called with correct args.
            # _assert_file_safe() resolves symlinks so we compare against the
            # resolved path, not the raw NamedTemporaryFile path.
            mock_client.add_file.assert_called_once_with(
                "test-notebook-123",
                str(Path(temp_path).resolve()),
                wait=False,
                wait_timeout=120.0,
            )

            # Verify return value
            assert result["status"] == "success"
            assert result["source_id"] == "test-source-id"
            assert result["source_type"] == "file"
        finally:
            Path(temp_path).unlink()

    def test_source_add_file_requires_path(self):
        """Test that file_path is required for source_type=file."""
        from notebooklm_tools.mcp.tools import sources

        result = sources.source_add(
            notebook_id="test-notebook",
            source_type="file",
            # Missing file_path
        )

        assert result["status"] == "error"
        assert "file_path is required" in result["error"]
