"""Regression tests for ``is_logged_in()`` URL detection.

Background: ``is_logged_in(url)`` previously used a substring match
(``if "accounts.google.com" in url``) against the full URL string. After
Google sign-in, NotebookLM appends ``?original_referer=https://accounts.google.com#``
to the redirect target, which caused the substring check to fire and
report "not logged in" -- making ``nlm login`` time out after 5 minutes
even though the browser was fully signed in.

The fix parses the URL hostname instead of substring-matching the full URL.
"""

import pytest

from notebooklm_tools.utils.cdp import is_logged_in


@pytest.mark.parametrize(
    "url, expected",
    [
        # Plain logged-in URLs.
        ("https://notebooklm.google.com/", True),
        ("https://notebooklm.google.com/some/notebook/abc", True),
        # Regression: NotebookLM appends ?original_referer=... right after
        # Google sign-in. The substring `accounts.google.com` IS present in
        # the URL (inside the query string), but the user is signed in.
        (
            "https://notebooklm.google.com/?original_referer=https%3A%2F%2Faccounts.google.com%23",
            True,
        ),
        # Defensive: an unrelated query string mentioning accounts.google.com
        # must not be confused with a sign-in redirect.
        ("https://notebooklm.google.com/?ref=https://accounts.google.com", True),
        # Enterprise NotebookLM host.
        ("https://notebooklm.cloud.google.com/", True),
        ("https://notebooklm.cloud.google.com/notebook/abc", True),
        # Standard Google sign-in redirect: not logged in.
        ("https://accounts.google.com/v3/signin/identifier?continue=...", False),
        ("https://accounts.google.com/", False),
        # Hostname spoofing on the accounts.google.com side must not be treated
        # as a sign-in redirect (the regression this PR fixes was the inverse:
        # treating a query-string mention of accounts.google.com as a redirect).
        ("https://evil.accounts.google.com.example.com/", False),
        # Unrelated domains.
        ("https://example.com/", False),
        # Edge cases: empty / malformed URLs must default to "not logged in".
        ("", False),
        ("not a url at all", False),
    ],
)
def test_is_logged_in(url: str, expected: bool) -> None:
    assert is_logged_in(url) is expected
