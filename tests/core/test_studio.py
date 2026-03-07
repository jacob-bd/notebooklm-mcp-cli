#!/usr/bin/env python3
"""Tests for StudioMixin."""

import pytest

from notebooklm_tools.core.base import BaseClient
from notebooklm_tools.core.studio import StudioMixin


class TestStudioMixinImport:
    """Test that StudioMixin can be imported correctly."""

    def test_studio_mixin_import(self):
        """Test that StudioMixin can be imported."""
        assert StudioMixin is not None

    def test_studio_mixin_inherits_base(self):
        """Test that StudioMixin inherits from BaseClient."""
        assert issubclass(StudioMixin, BaseClient)

    def test_studio_mixin_has_creation_methods(self):
        """Test that StudioMixin has creation methods."""
        expected_methods = [
            "create_audio_overview",
            "create_video_overview",
            "create_infographic",
            "create_slide_deck",
            "create_report",
            "create_flashcards",
            "create_quiz",
            "create_data_table",
        ]
        for method in expected_methods:
            assert hasattr(StudioMixin, method), f"Missing method: {method}"

    def test_studio_mixin_has_status_methods(self):
        """Test that StudioMixin has status methods."""
        expected_methods = [
            "poll_studio_status",
            "get_studio_status",
            "delete_studio_artifact",
            "delete_mind_map",
        ]
        for method in expected_methods:
            assert hasattr(StudioMixin, method), f"Missing method: {method}"

    def test_studio_mixin_has_mind_map_methods(self):
        """Test that StudioMixin has mind map methods."""
        expected_methods = [
            "generate_mind_map",
            "save_mind_map",
            "list_mind_maps",
        ]
        for method in expected_methods:
            assert hasattr(StudioMixin, method), f"Missing method: {method}"


class TestStudioMixinMethods:
    """Test StudioMixin method behavior."""

    def test_create_report_validates_format(self):
        """Test that create_report validates report_format parameter."""
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        with pytest.raises(ValueError, match="Invalid report_format"):
            mixin.create_report("notebook-id", ["source-id"], report_format="invalid")

    def test_get_studio_status_is_alias(self):
        """Test that get_studio_status is an alias for poll_studio_status."""
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")
        
        # Verify method exists and is callable
        assert callable(mixin.get_studio_status)
        # Method docstring should indicate it's an alias
        assert "Alias" in mixin.get_studio_status.__doc__


class TestCinematicVideoConstant:
    """Test that the Cinematic video format constant is correctly defined."""

    def test_cinematic_constant_value(self):
        """VIDEO_FORMAT_CINEMATIC should be 3."""
        from notebooklm_tools.core import constants
        assert constants.VIDEO_FORMAT_CINEMATIC == 3

    def test_cinematic_code_mapper_lookup(self):
        """CodeMapper should resolve 'cinematic' to 3 and back."""
        from notebooklm_tools.core import constants
        assert constants.VIDEO_FORMATS.get_code("cinematic") == 3
        assert constants.VIDEO_FORMATS.get_name(3) == "cinematic"
