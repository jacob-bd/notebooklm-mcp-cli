#!/usr/bin/env python3
"""Tests for StudioMixin."""

from unittest.mock import MagicMock

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

    def test_normalize_studio_status_treats_audio_status_2_with_media_as_completed(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")

        artifact_data = [
            "art-1",
            "Audio Artifact",
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

        assert mixin._normalize_studio_status(artifact_data) == "completed"

    def test_normalize_studio_status_keeps_unverified_code_unknown(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")

        artifact_data = [
            "art-2",
            "Unknown Artifact",
            mixin.STUDIO_TYPE_REPORT,
            [],
            2,
        ]

        assert mixin._normalize_studio_status(artifact_data) == "unknown"

    def test_normalize_studio_status_handles_non_list_payloads(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")

        assert mixin._normalize_studio_status("unexpected-payload") == "unknown"
        assert mixin._normalize_studio_status({"status": 3}) == "unknown"
        assert mixin._normalize_studio_status(["too-short"]) == "unknown"

    def test_extract_audio_media_url_prefers_media_list_over_thumbnail_slot(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")

        artifact_data = [
            "art-1",
            "Audio Artifact",
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
                [
                    ["https://example.com/audio-stream.m3u8", 2],
                    ["https://example.com/audio.m4a", 1, "audio/mp4"],
                ],
                [],
            ],
        ]

        assert mixin._extract_audio_media_url(artifact_data) == "https://example.com/audio.m4a"

    def test_poll_studio_status_uses_normalized_status_mapping(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")
        http_client = MagicMock()
        http_client.post.return_value = MagicMock(
            text="unused",
            raise_for_status=lambda: None,
        )

        mixin._get_client = MagicMock(return_value=http_client)
        mixin._build_request_body = MagicMock(return_value="body")
        mixin._build_url = MagicMock(return_value="url")
        mixin._parse_response = MagicMock(return_value=["parsed"])
        mixin._extract_rpc_result = MagicMock(
            return_value=[
                [
                    [
                        "art-1",
                        "Audio Artifact",
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
                ]
            ]
        )

        result = mixin.poll_studio_status("nb-1")

        assert result[0]["status"] == "completed"
        assert result[0]["audio_url"] == "https://example.com/audio.m4a"

    def test_create_audio_overview_uses_normalized_status_mapping(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")
        http_client = MagicMock()
        http_client.post.return_value = MagicMock(
            text="unused",
            raise_for_status=lambda: None,
        )

        mixin._get_client = MagicMock(return_value=http_client)
        mixin._build_request_body = MagicMock(return_value="body")
        mixin._build_url = MagicMock(return_value="url")
        mixin._parse_response = MagicMock(return_value=["parsed"])
        mixin._extract_rpc_result = MagicMock(
            return_value=[
                [
                    "art-1",
                    "Audio Artifact",
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
            ]
        )

        result = mixin.create_audio_overview("nb-1", ["src-1"])

        assert result["status"] == "completed"

    def test_create_audio_overview_keeps_unknown_for_unexpected_payload_shape(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")
        http_client = MagicMock()
        http_client.post.return_value = MagicMock(
            text="unused",
            raise_for_status=lambda: None,
        )

        mixin._get_client = MagicMock(return_value=http_client)
        mixin._build_request_body = MagicMock(return_value="body")
        mixin._build_url = MagicMock(return_value="url")
        mixin._parse_response = MagicMock(return_value=["parsed"])
        mixin._extract_rpc_result = MagicMock(return_value=["unexpected-payload"])

        result = mixin.create_audio_overview("nb-1", ["src-1"])

        assert result["artifact_id"] is None
        assert result["status"] == "unknown"

    def test_revise_slide_deck_uses_normalized_failed_status(self):
        mixin = StudioMixin(cookies={"test": "cookie"}, csrf_token="test")
        mixin._call_rpc = MagicMock(return_value=[["art-2", "Revised Deck", 8, None, 4]])

        result = mixin.revise_slide_deck("art-1", [(0, "Tighten slide title")])

        assert result == {
            "artifact_id": "art-2",
            "title": "Revised Deck",
            "original_artifact_id": "art-1",
            "status": "failed",
        }


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

    def test_custom_style_code_mapper_lookup(self):
        """CodeMapper should resolve 'custom' to 2 and back."""
        from notebooklm_tools.core import constants

        assert constants.VIDEO_STYLES.get_code("custom") == 2
        assert constants.VIDEO_STYLES.get_name(2) == "custom"
