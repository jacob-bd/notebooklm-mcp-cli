"""Tests for cookie parsing from files (Netscape format support)."""

import json
import tempfile
from pathlib import Path

import pytest

from notebooklm_tools.core.exceptions import AuthenticationError
from notebooklm_tools.utils.browser import parse_cookies_from_file

# --- JSON format ---


def test_parse_json_dict():
    """JSON dict format: {"name": "value"}."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"SID": "abc123", "HSID": "def456"}, f)
        path = f.name
    try:
        result = parse_cookies_from_file(path)
        assert result == {"SID": "abc123", "HSID": "def456"}
    finally:
        Path(path).unlink(missing_ok=True)


# --- Netscape format ---

SAMPLE_NETSCAPE = """# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

.google.com\tTRUE\t/\tFALSE\t1788094158\tSEARCH_SAMESITE\tCgQIo6AB
.google.com\tTRUE\t/\tTRUE\t1788094158\t__Secure-BUCKET\tCMID
.google.com\tTRUE\t/\tFALSE\t1812953356\tSID\tsid-value-123
.google.com\tTRUE\t/\tTRUE\t1812953356\tHSID\tA1SAks--UQ
.google.com\tTRUE\t/\tTRUE\t1812953356\tSSID\tAYOTqrMe
.google.com\tTRUE\t/\tFALSE\t1812953356\tAPISID\tapi-value-789
.google.com\tTRUE\t/\tTRUE\t1812953356\tSAPISID\tsapi-value-000
notebooklm.google.com\tFALSE\t/\tTRUE\t1814162423\tOSID\tosid-value-111
"""


def test_parse_netscape_format():
    """Netscape cookie file with tab-separated fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_NETSCAPE)
        path = f.name
    try:
        result = parse_cookies_from_file(path)
        assert result["SID"] == "sid-value-123"
        assert result["HSID"] == "A1SAks--UQ"
        assert result["SSID"] == "AYOTqrMe"
        assert result["APISID"] == "api-value-789"
        assert result["SAPISID"] == "sapi-value-000"
        assert result["OSID"] == "osid-value-111"
        assert result["SEARCH_SAMESITE"] == "CgQIo6AB"
        assert result["__Secure-BUCKET"] == "CMID"
        assert len(result) == 8
    finally:
        Path(path).unlink(missing_ok=True)


def test_netscape_passes_validation():
    """Netscape cookies should pass validate_notebooklm_cookies."""
    from notebooklm_tools.utils.browser import validate_notebooklm_cookies

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_NETSCAPE)
        path = f.name
    try:
        result = parse_cookies_from_file(path)
        assert validate_notebooklm_cookies(result) is True
    finally:
        Path(path).unlink(missing_ok=True)


def test_netscape_skips_blank_and_comments():
    """Blank lines and comments starting with # are skipped."""
    content = """# Header comment
# Another comment

.google.com\tTRUE\t/\tTRUE\t1\tMYCOOKIE\tmyvalue

"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        result = parse_cookies_from_file(path)
        assert result == {"MYCOOKIE": "myvalue"}
    finally:
        Path(path).unlink(missing_ok=True)


def test_non_netscape_tab_content_ignored():
    """Content with tabs but not 7+ fields per line falls through."""
    content = "just\ta\tfew\tfields\nnot\tenough"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        with pytest.raises(AuthenticationError, match="Could not parse cookies"):
            parse_cookies_from_file(path)
    finally:
        Path(path).unlink(missing_ok=True)


# --- Cookie header format (existing, ensure not broken) ---


def test_parse_cookie_header():
    """Standard Cookie header format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Cookie: SID=abc; HSID=def; SSID=ghi")
        path = f.name
    try:
        result = parse_cookies_from_file(path)
        assert result == {"SID": "abc", "HSID": "def", "SSID": "ghi"}
    finally:
        Path(path).unlink(missing_ok=True)


def test_parse_name_value_pairs():
    """Plain name=value pairs separated by semicolons."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("SID=abc; HSID=def; SSID=ghi")
        path = f.name
    try:
        result = parse_cookies_from_file(path)
        assert result == {"SID": "abc", "HSID": "def", "SSID": "ghi"}
    finally:
        Path(path).unlink(missing_ok=True)


def test_file_not_found():
    """Missing file raises AuthenticationError."""
    with pytest.raises(AuthenticationError, match="Cookie file not found"):
        parse_cookies_from_file("/tmp/nonexistent_cookie_file_xyz.txt")
