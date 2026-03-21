"""Helper-focused tests for auth and sync CLIs."""

import json
from pathlib import Path

from notebooklm_mcp import auth_cli, sync_cli


class _Notebook:
    def __init__(self, notebook_id: str, title: str):
        self.id = notebook_id
        self.title = title


class _ListClient:
    def list_notebooks(self):
        return [
            _Notebook("nb-1", "Notebook One"),
            _Notebook("nb-2", "Notebook Two"),
        ]


def test_check_if_logged_in_by_url_uses_domain_signal():
    """URL-based login detection should accept NotebookLM and reject account redirects."""
    assert auth_cli.check_if_logged_in_by_url("https://notebooklm.google.com/notebook/123") is True
    assert auth_cli.check_if_logged_in_by_url("https://accounts.google.com/signin/v2") is False
    assert auth_cli.check_if_logged_in_by_url("https://example.com/") is False


def test_extract_session_id_from_html_supports_known_patterns():
    """Session ID parsing should match each of the known markup patterns."""
    assert auth_cli.extract_session_id_from_html('"FdrFJe":"12345"') == "12345"
    assert auth_cli.extract_session_id_from_html('f.sid = 67890') == "67890"
    assert auth_cli.extract_session_id_from_html('"cfb2h":"session-token"') == "session-token"
    assert auth_cli.extract_session_id_from_html("<html></html>") == ""


def test_is_chrome_profile_locked_checks_singleton_lock(tmp_path: Path):
    """Profile lock detection should key off the Chrome SingletonLock file."""
    profile_dir = tmp_path / "chrome-profile"
    profile_dir.mkdir()

    assert auth_cli.is_chrome_profile_locked(str(profile_dir)) is False

    (profile_dir / "SingletonLock").write_text("")
    assert auth_cli.is_chrome_profile_locked(str(profile_dir)) is True


def test_find_notebook_helpers_match_exact_id_and_title():
    """Notebook lookups should perform exact matches over the listed notebooks."""
    client = _ListClient()

    assert sync_cli.find_notebook_by_id(client, "nb-2").title == "Notebook Two"
    assert sync_cli.find_notebook_by_name(client, "Notebook One").id == "nb-1"
    assert sync_cli.find_notebook_by_name(client, "Missing") is None


def test_discover_tier3_docs_collects_root_and_nested_markdown(tmp_path: Path):
    """Tier 3 discovery should include root docs plus one-level nested markdown files."""
    (tmp_path / "README.md").write_text("# Readme")
    (tmp_path / "CLAUDE.md").write_text("# Claude")
    (tmp_path / "PROJECT_PRIMER.md").write_text("# Primer")
    (tmp_path / "RELATIONS.yaml").write_text("links: []")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# Guide")
    (docs_dir / "ignore.txt").write_text("ignore")
    nested_docs = docs_dir / "nested"
    nested_docs.mkdir()
    (nested_docs / "nested.md").write_text("# Nested")

    ten_docs_dir = tmp_path / "10_docs"
    ten_docs_dir.mkdir()
    (ten_docs_dir / "plan.md").write_text("# Plan")
    nested_ten_docs = ten_docs_dir / "notes"
    nested_ten_docs.mkdir()
    (nested_ten_docs / "note.md").write_text("# Note")

    discovered = sync_cli.discover_tier3_docs(tmp_path)
    discovered_names = sorted(path.relative_to(tmp_path).as_posix() for path in discovered)

    assert discovered_names == [
        "10_docs/notes/note.md",
        "10_docs/plan.md",
        "CLAUDE.md",
        "PROJECT_PRIMER.md",
        "README.md",
        "RELATIONS.yaml",
        "docs/guide.md",
        "docs/nested/nested.md",
    ]


def test_write_receipt_summarizes_actions(monkeypatch, tmp_path: Path):
    """Sync receipts should persist notebook metadata and action counts."""
    monkeypatch.setattr(sync_cli, "RECEIPTS_DIR", tmp_path)

    receipt_path = sync_cli.write_receipt(
        repo_id="C021_notebooklm-mcp",
        notebook_name="NotebookLM MCP",
        notebook_id="notebook-123",
        files_synced=[
            {"action": "added", "path": "README.md"},
            {"action": "replaced", "path": "CLAUDE.md"},
            {"action": "skipped", "path": "PROJECT_PRIMER.md"},
            {"action": "failed", "path": "docs/CLI.md"},
        ],
        audio_requested=True,
        audio_focus="Sync summary",
    )

    payload = json.loads(receipt_path.read_text())

    assert payload["repo_id"] == "C021_notebooklm-mcp"
    assert payload["notebook_url"] == "https://notebooklm.google.com/notebook/notebook-123"
    assert payload["summary"] == {
        "total": 4,
        "added": 1,
        "replaced": 1,
        "skipped": 1,
        "failed": 1,
    }
    assert payload["audio_overview"] == {
        "requested": True,
        "focus": "Sync summary",
    }


def test_write_batch_receipt_persists_summary(monkeypatch, tmp_path: Path):
    """Batch receipts should write the supplied summary alongside mode metadata."""
    monkeypatch.setattr(sync_cli, "RECEIPTS_DIR", tmp_path)

    receipt_path = sync_cli.write_batch_receipt({"repos_processed": 3, "failures": 1})
    payload = json.loads(receipt_path.read_text())

    assert payload["mode"] == "batch_refresh"
    assert payload["repos_processed"] == 3
    assert payload["failures"] == 1


def test_append_refresh_log_rotates_oversized_log(monkeypatch, tmp_path: Path):
    """Large refresh logs should rotate before new lines are appended."""
    log_path = tmp_path / "refresh.log"
    log_path.write_text("123456")
    monkeypatch.setattr(sync_cli, "REFRESH_LOG_PATH", log_path)
    monkeypatch.setattr(sync_cli, "MAX_REFRESH_LOG_BYTES", 5)

    sync_cli.append_refresh_log(["fresh line"])

    rotated_logs = list(tmp_path.glob("refresh.log.*.bak"))
    assert len(rotated_logs) == 1
    assert rotated_logs[0].read_text() == "123456"
    assert log_path.read_text() == "fresh line\n"
