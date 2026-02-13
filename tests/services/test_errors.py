"""Tests for services.errors module."""

import pytest
from notebooklm_tools.services.errors import (
    ServiceError,
    ValidationError,
    NotFoundError,
    CreationError,
    ExportError,
)


class TestServiceError:
    """Test the base ServiceError class."""

    def test_basic_message(self):
        err = ServiceError("something broke")
        assert str(err) == "something broke"
        assert err.user_message == "something broke"
        assert err.debug_code is None

    def test_custom_user_message(self):
        err = ServiceError(
            "Internal: API returned 500",
            user_message="Export failed, please try again.",
        )
        assert str(err) == "Internal: API returned 500"
        assert err.user_message == "Export failed, please try again."

    def test_debug_code(self):
        err = ServiceError(
            "fail",
            debug_code="EXPORT_NO_URL",
        )
        assert err.debug_code == "EXPORT_NO_URL"

    def test_user_message_defaults_to_message(self):
        err = ServiceError("same message")
        assert err.user_message == "same message"


class TestErrorHierarchy:
    """Ensure all errors inherit from ServiceError."""

    @pytest.mark.parametrize("error_class", [
        ValidationError,
        NotFoundError,
        CreationError,
        ExportError,
    ])
    def test_inherits_from_service_error(self, error_class):
        err = error_class("test")
        assert isinstance(err, ServiceError)
        assert isinstance(err, Exception)

    @pytest.mark.parametrize("error_class", [
        ValidationError,
        NotFoundError,
        CreationError,
        ExportError,
    ])
    def test_subclass_preserves_user_message(self, error_class):
        err = error_class("internal", user_message="user-facing")
        assert err.user_message == "user-facing"
