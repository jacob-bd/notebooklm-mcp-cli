"""Tests for the `nlm source add` CLI command, focusing on --youtube bulk support."""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from notebooklm_tools.cli.commands.source import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.__enter__ = lambda s: s
    client.__exit__ = MagicMock(return_value=False)
    client.add_url_source.return_value = {"id": "src-1", "title": "YouTube Video"}
    return client


def _patch_deps(mock_client, add_source_result=None, add_sources_result=None):
    """Return a list of context-manager patches for CLI dependencies."""
    alias_mgr = MagicMock()
    alias_mgr.resolve.side_effect = lambda x: x  # identity

    single_result = add_source_result or {"source_type": "url", "source_id": "src-1", "title": "YouTube Video"}
    bulk_result = add_sources_result or {
        "results": [
            {"source_type": "url", "source_id": "src-1", "title": "Video A"},
            {"source_type": "url", "source_id": "src-2", "title": "Video B"},
        ],
        "added_count": 2,
    }

    return [
        patch("notebooklm_tools.cli.commands.source.get_alias_manager", return_value=alias_mgr),
        patch("notebooklm_tools.cli.commands.source.get_client", return_value=mock_client),
        patch("notebooklm_tools.cli.commands.source.sources_service.add_source", return_value=single_result),
        patch("notebooklm_tools.cli.commands.source.sources_service.add_sources", return_value=bulk_result),
    ]


class TestYoutubeSingle:
    """Single --youtube flag: existing behaviour must be preserved."""

    def test_single_youtube_calls_add_source(self, runner, mock_client):
        with _patch_deps(mock_client)[0], _patch_deps(mock_client)[1], \
             patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias, \
             patch("notebooklm_tools.cli.commands.source.get_client") as m_client, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_source") as m_add, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_sources") as m_bulk:

            m_alias.return_value.resolve.side_effect = lambda x: x
            m_client.return_value = mock_client
            m_add.return_value = {"source_type": "url", "source_id": "src-1", "title": "My Video"}
            m_bulk.return_value = {"results": [], "added_count": 0}

            result = runner.invoke(app, ["add", "nb-123", "--youtube", "https://youtu.be/abc"])

        assert result.exit_code == 0
        m_add.assert_called_once()
        call_kwargs = m_add.call_args
        assert call_kwargs.kwargs["url"] == "https://youtu.be/abc"
        m_bulk.assert_not_called()

    def test_single_youtube_output_shows_title(self, runner, mock_client):
        with patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias, \
             patch("notebooklm_tools.cli.commands.source.get_client") as m_client, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_source") as m_add, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_sources"):

            m_alias.return_value.resolve.side_effect = lambda x: x
            m_client.return_value = mock_client
            m_add.return_value = {"source_type": "url", "source_id": "src-1", "title": "My Video"}

            result = runner.invoke(app, ["add", "nb-123", "--youtube", "https://youtu.be/abc"])

        assert result.exit_code == 0
        assert "My Video" in result.output


class TestYoutubeBulk:
    """Multiple --youtube flags: new bulk behaviour."""

    def test_bulk_youtube_calls_add_sources(self, runner, mock_client):
        bulk_result = {
            "results": [
                {"source_type": "url", "source_id": "src-1", "title": "Video A"},
                {"source_type": "url", "source_id": "src-2", "title": "Video B"},
            ],
            "added_count": 2,
        }

        with patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias, \
             patch("notebooklm_tools.cli.commands.source.get_client") as m_client, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_source") as m_add, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_sources") as m_bulk:

            m_alias.return_value.resolve.side_effect = lambda x: x
            m_client.return_value = mock_client
            m_bulk.return_value = bulk_result

            result = runner.invoke(app, [
                "add", "nb-123",
                "--youtube", "https://youtu.be/aaa",
                "--youtube", "https://youtu.be/bbb",
            ])

        assert result.exit_code == 0
        m_add.assert_not_called()
        m_bulk.assert_called_once()
        sources_arg = m_bulk.call_args.args[2]
        assert sources_arg == [
            {"source_type": "url", "url": "https://youtu.be/aaa"},
            {"source_type": "url", "url": "https://youtu.be/bbb"},
        ]

    def test_bulk_youtube_output_shows_count_and_titles(self, runner, mock_client):
        bulk_result = {
            "results": [
                {"source_type": "url", "source_id": "src-1", "title": "Video A"},
                {"source_type": "url", "source_id": "src-2", "title": "Video B"},
            ],
            "added_count": 2,
        }

        with patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias, \
             patch("notebooklm_tools.cli.commands.source.get_client") as m_client, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_source"), \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_sources") as m_bulk:

            m_alias.return_value.resolve.side_effect = lambda x: x
            m_client.return_value = mock_client
            m_bulk.return_value = bulk_result

            result = runner.invoke(app, [
                "add", "nb-123",
                "--youtube", "https://youtu.be/aaa",
                "--youtube", "https://youtu.be/bbb",
            ])

        assert result.exit_code == 0
        assert "Video A" in result.output
        assert "Video B" in result.output
        assert "2 source(s) added" in result.output

    def test_bulk_youtube_three_urls(self, runner, mock_client):
        bulk_result = {
            "results": [{"source_type": "url", "source_id": f"src-{i}", "title": f"Video {i}"} for i in range(3)],
            "added_count": 3,
        }

        with patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias, \
             patch("notebooklm_tools.cli.commands.source.get_client") as m_client, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_source"), \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_sources") as m_bulk:

            m_alias.return_value.resolve.side_effect = lambda x: x
            m_client.return_value = mock_client
            m_bulk.return_value = bulk_result

            result = runner.invoke(app, [
                "add", "nb-123",
                "-y", "https://youtu.be/a",
                "-y", "https://youtu.be/b",
                "-y", "https://youtu.be/c",
            ])

        assert result.exit_code == 0
        sources_arg = m_bulk.call_args.args[2]
        assert len(sources_arg) == 3


class TestMixedUrlAndYoutube:
    """--url and --youtube together should both be treated as URLs in bulk."""

    def test_url_and_youtube_together_use_bulk_path(self, runner, mock_client):
        bulk_result = {
            "results": [
                {"source_type": "url", "source_id": "src-1", "title": "Web Page"},
                {"source_type": "url", "source_id": "src-2", "title": "YouTube Video"},
            ],
            "added_count": 2,
        }

        with patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias, \
             patch("notebooklm_tools.cli.commands.source.get_client") as m_client, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_source") as m_add, \
             patch("notebooklm_tools.cli.commands.source.sources_service.add_sources") as m_bulk:

            m_alias.return_value.resolve.side_effect = lambda x: x
            m_client.return_value = mock_client
            m_bulk.return_value = bulk_result

            result = runner.invoke(app, [
                "add", "nb-123",
                "--url", "https://example.com",
                "--youtube", "https://youtu.be/abc",
            ])

        # --url and --youtube are different source types, should be rejected
        assert result.exit_code != 0
        assert "one source type" in result.output
        m_add.assert_not_called()
        m_bulk.assert_not_called()


class TestYoutubeValidation:
    """Input validation edge cases."""

    def test_no_source_type_errors(self, runner):
        result = runner.invoke(app, ["add", "nb-123"])
        assert result.exit_code != 0
        assert "specify a source" in result.output

    def test_youtube_and_text_together_errors(self, runner, mock_client):
        with patch("notebooklm_tools.cli.commands.source.get_alias_manager") as m_alias:
            m_alias.return_value.resolve.side_effect = lambda x: x

            result = runner.invoke(app, [
                "add", "nb-123",
                "--youtube", "https://youtu.be/abc",
                "--text", "some text",
            ])

        assert result.exit_code != 0
        assert "one source type" in result.output
