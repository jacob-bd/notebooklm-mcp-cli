"""Tests for NotebookMixin class."""

import pytest
from unittest.mock import patch, MagicMock


def test_notebook_mixin_import():
    """Test that NotebookMixin can be imported."""
    from notebooklm_tools.core.notebooks import NotebookMixin
    assert NotebookMixin is not None


def test_notebook_mixin_inherits_base():
    """Test that NotebookMixin inherits from BaseClient."""
    from notebooklm_tools.core.notebooks import NotebookMixin
    from notebooklm_tools.core.base import BaseClient
    assert issubclass(NotebookMixin, BaseClient)


def test_notebook_mixin_has_methods():
    """Test that NotebookMixin has all expected methods."""
    from notebooklm_tools.core.notebooks import NotebookMixin
    
    expected_methods = [
        'list_notebooks',
        'get_notebook',
        'get_notebook_summary',
        'create_notebook',
        'rename_notebook',
        'configure_chat',
        'delete_notebook',
    ]
    
    for method_name in expected_methods:
        assert hasattr(NotebookMixin, method_name), f"Missing method: {method_name}"


def test_list_notebooks_uses_correct_rpc():
    """Test that list_notebooks calls _call_rpc with the correct RPC ID."""
    from notebooklm_tools.core.notebooks import NotebookMixin

    with patch.object(NotebookMixin, '_refresh_auth_tokens'):
        with patch.object(NotebookMixin, '_call_rpc') as mock_rpc:
            mock_rpc.return_value = []

            mixin = NotebookMixin(cookies={"test": "cookie"}, csrf_token="test")
            mixin.list_notebooks()

            # Verify correct RPC ID was used
            mock_rpc.assert_called_once()
            assert mock_rpc.call_args[0][0] == "wXbhsf"  # RPC_LIST_NOTEBOOKS


def test_create_notebook_uses_correct_rpc():
    """Test that create_notebook calls the correct RPC."""
    from notebooklm_tools.core.notebooks import NotebookMixin
    
    with patch.object(NotebookMixin, '_refresh_auth_tokens'):
        with patch.object(NotebookMixin, '_call_rpc') as mock_rpc:
            mock_rpc.return_value = ["title", None, "notebook_id_123"]
            
            mixin = NotebookMixin(cookies={"test": "cookie"}, csrf_token="test")
            mixin.create_notebook("Test Notebook")
            
            mock_rpc.assert_called_once()
            call_args = mock_rpc.call_args
            assert call_args[0][0] == "CCqFvf"  # RPC_CREATE_NOTEBOOK


def test_delete_notebook_uses_correct_rpc():
    """Test that delete_notebook calls _call_rpc with the correct RPC ID."""
    from notebooklm_tools.core.notebooks import NotebookMixin

    with patch.object(NotebookMixin, '_refresh_auth_tokens'):
        with patch.object(NotebookMixin, '_call_rpc') as mock_rpc:
            mock_rpc.return_value = {}  # Non-None means success

            mixin = NotebookMixin(cookies={"test": "cookie"}, csrf_token="test")
            result = mixin.delete_notebook("notebook_id_123")

            # Verify correct RPC ID was used
            mock_rpc.assert_called_once()
            assert mock_rpc.call_args[0][0] == "WWINqb"  # RPC_DELETE_NOTEBOOK
            assert result is True  # Should return True on success
