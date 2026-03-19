import pytest
from types import SimpleNamespace
from unittest.mock import patch

from notebooklm_tools.cli.formatters import (
    JsonFormatter,
    OutputFormat,
    detect_output_format,
    print_json,
)

def test_detect_output_format_json_flag():
    # Flag takes precedence
    assert detect_output_format(json_flag=True) == OutputFormat.JSON

def test_detect_output_format_tty():
    # TTY = Table
    with patch("sys.stdout.isatty", return_value=True):
        assert detect_output_format() == OutputFormat.TABLE

def test_detect_output_format_no_tty():
    # No TTY = JSON (auto-detect)
    with patch("sys.stdout.isatty", return_value=False):
        assert detect_output_format() == OutputFormat.JSON

def test_detect_output_format_quiet_flag():
    # Quiet = Compact (unless JSON specified)
    assert detect_output_format(quiet_flag=True) == OutputFormat.COMPACT
    
    # JSON flag overrides quiet
    assert detect_output_format(json_flag=True, quiet_flag=True) == OutputFormat.JSON

def test_detect_output_format_title_flag():
    # Title flag implies compact/list mode in current implementation
    with patch("sys.stdout.isatty", return_value=True):
        assert detect_output_format(title_flag=True) == OutputFormat.COMPACT


def test_print_json_preserves_non_ascii(capsys):
    print_json({"title": "café", "greeting": "こんにちは"})

    output = capsys.readouterr().out

    assert '"title": "café"' in output
    assert '"greeting": "こんにちは"' in output
    assert "\\u00e9" not in output
    assert "\\u3053" not in output


def test_json_formatter_format_notebooks_preserves_non_ascii(capsys):
    formatter = JsonFormatter()
    notebooks = [SimpleNamespace(id="nb-1", title="Café notes", source_count=2)]

    formatter.format_notebooks(notebooks)

    output = capsys.readouterr().out

    assert '"title": "Café notes"' in output
    assert "\\u00e9" not in output
