"""Tests that verb command fallback defaults match valid CodeMapper values.

Verbs in verbs.py use `xxx or "fallback"` patterns to provide defaults
when the user doesn't specify an option. These fallbacks must match the
valid names in core/constants.py CodeMapper instances, otherwise the
downstream service/core layer will reject them.
"""

import pytest

from notebooklm_tools.core import constants


class TestAudioVerbDefaults:
    """Verify create_audio_verb fallback defaults are valid."""

    def test_format_default_is_valid(self):
        assert "deep_dive" in constants.AUDIO_FORMATS.names

    def test_length_default_is_valid(self):
        assert "default" in constants.AUDIO_LENGTHS.names


class TestVideoVerbDefaults:
    """Verify create_video_verb fallback defaults are valid."""

    def test_format_default_is_valid(self):
        assert "explainer" in constants.VIDEO_FORMATS.names

    def test_style_default_is_valid(self):
        assert "auto_select" in constants.VIDEO_STYLES.names


class TestReportVerbDefaults:
    """Verify create_report_verb fallback defaults are valid."""

    def test_format_default_is_valid(self):
        assert "Briefing Doc" == constants.REPORT_FORMAT_BRIEFING_DOC


class TestSlidesVerbDefaults:
    """Verify create_slides_verb fallback defaults are valid."""

    def test_format_default_is_valid(self):
        assert "detailed_deck" in constants.SLIDE_DECK_FORMATS.names

    def test_length_default_is_valid(self):
        assert "default" in constants.SLIDE_DECK_LENGTHS.names


class TestInfographicVerbDefaults:
    """Verify create_infographic_verb fallback defaults are valid."""

    def test_orientation_default_is_valid(self):
        assert "landscape" in constants.INFOGRAPHIC_ORIENTATIONS.names

    def test_detail_default_is_valid(self):
        assert "standard" in constants.INFOGRAPHIC_DETAILS.names


class TestFlashcardsVerbDefaults:
    """Verify create_flashcards_verb fallback defaults are valid."""

    def test_difficulty_default_is_valid(self):
        assert "medium" in constants.FLASHCARD_DIFFICULTIES.names


class TestAllVerbDefaultsConsistency:
    """Cross-check that verbs.py fallback strings resolve without error."""

    @pytest.mark.parametrize("name,mapper", [
        ("deep_dive", constants.AUDIO_FORMATS),
        ("default", constants.AUDIO_LENGTHS),
        ("explainer", constants.VIDEO_FORMATS),
        ("auto_select", constants.VIDEO_STYLES),
        ("detailed_deck", constants.SLIDE_DECK_FORMATS),
        ("default", constants.SLIDE_DECK_LENGTHS),
        ("landscape", constants.INFOGRAPHIC_ORIENTATIONS),
        ("standard", constants.INFOGRAPHIC_DETAILS),
        ("medium", constants.FLASHCARD_DIFFICULTIES),
    ])
    def test_default_resolves_to_valid_code(self, name, mapper):
        code = mapper.get_code(name)
        assert isinstance(code, int)
