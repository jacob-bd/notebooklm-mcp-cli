
import pytest
from unittest.mock import patch, Mock
import sys
from notebooklm_tools.cli.formatters import detect_output_format, OutputFormat

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

