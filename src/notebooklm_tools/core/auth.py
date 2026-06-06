"""Authentication helper for NotebookLM MCP CLI.

Uses Chrome DevTools MCP to extract auth tokens from an authenticated browser session.
If the user is not logged in, prompts them to log in via the Chrome window.

Storage location: ~/.notebooklm-mcp-cli/ (unified for CLI and MCP)
"""

import contextlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from notebooklm_tools.utils.config import get_base_url

# Use logging instead of print to avoid corrupting MCP stdio protocol
logger = logging.getLogger(__name__)


@dataclass
class AuthTokens:
    """Authentication tokens for NotebookLM.

    Only cookies are required. CSRF token and session ID are optional because
    they can be auto-extracted from the NotebookLM page when needed.
    """

    cookies: dict[str, str]
    csrf_token: str = ""  # Optional - auto-extracted from page
    session_id: str = ""  # Optional - auto-extracted from page
    build_label: str = ""  # Optional - auto-extracted from page (cfb2h key)
    extracted_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "session_id": self.session_id,
            "build_label": self.build_label,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthTokens":
        return cls(
            cookies=data["cookies"],
            csrf_token=data.get("csrf_token", ""),
            session_id=data.get("session_id", ""),
            build_label=data.get("build_label", ""),
            extracted_at=data.get("extracted_at", 0),
        )

    def is_expired(self, max_age_hours: float = 168) -> bool:
        """Check if cookies are older than max_age_hours.

        Default is 168 hours (1 week) since cookies are stable for weeks.
        The CSRF token/session ID will be auto-refreshed regardless.
        """
        age_seconds = time.time() - self.extracted_at
        return age_seconds > (max_age_hours * 3600)

    @property
    def cookie_header(self) -> str:
        """Get cookies as a header string."""
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())


def get_cache_path() -> Path:
    """Get the path to the auth cache file.

    Uses ~/.notebooklm-mcp-cli/auth.json (unified location).
    """
    from notebooklm_tools.utils.config import get_auth_cache_file

    return get_auth_cache_file()


def load_cached_tokens() -> AuthTokens | None:
    """Load tokens from cache (default profile or legacy file).

    Note: We no longer reject tokens based on age. The functional check
    (redirect to login during CSRF refresh) is the real validity test.
    Cookies often last much longer than any arbitrary time limit.
    """
    # 1. Try default profile first (Unified Auth)
    try:
        manager = get_auth_manager()
        if manager.profile_exists():
            profile = manager.load_profile()
            return AuthTokens(
                cookies=profile.cookies,
                csrf_token=profile.csrf_token or "",
                session_id=profile.session_id or "",
                extracted_at=(
                    profile.last_validated.timestamp() if profile.last_validated else time.time()
                ),
            )
    except Exception as e:
        logger.debug(f"Failed to load default profile: {e}")

    # 2. Fallback to legacy auth cache (with auto-migration)
    cache_path = get_cache_path()

    # Auto-migrate from old location if needed
    if not cache_path.exists():
        from notebooklm_tools.utils.config import auto_migrate_if_needed

        auto_migrate_if_needed()

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        tokens = AuthTokens.from_dict(data)

        # Just warn if tokens are old, but still return them
        # Let the API client's functional check determine validity
        if tokens.is_expired():
            logger.warning("Cached tokens are older than 1 week. They may still work.")

        return tokens
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to load cached tokens: {e}")
        return None


def save_tokens_to_cache(tokens: AuthTokens, silent: bool = False) -> None:
    """Save tokens to both the legacy auth.json and the active profile.

    Writing to both locations ensures the MCP server and CLI always read
    the same credentials regardless of which code path loads them.
    See: https://github.com/jacob-bd/notebooklm-mcp-cli/issues/169

    Args:
        tokens: AuthTokens to save
        silent: If True, don't print confirmation message (for auto-updates)
    """
    cache_path = get_cache_path()
    fd = os.open(str(cache_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        f = os.fdopen(fd, "w", encoding="utf-8")
    except BaseException:
        os.close(fd)
        raise
    with f:
        json.dump(tokens.to_dict(), f, indent=2)

    # Also update the default profile so load_cached_tokens() (which
    # checks profiles first) picks up the same tokens.
    try:
        manager = get_auth_manager()
        if manager.profile_exists():
            manager.save_profile(
                cookies=tokens.cookies,
                csrf_token=tokens.csrf_token or None,
                session_id=tokens.session_id or None,
                build_label=tokens.build_label or None,
                force=True,
            )
    except Exception as e:
        logger.debug(f"Failed to sync tokens to profile: {e}")

    if not silent:
        logger.info(f"Auth tokens cached to {cache_path}")


def extract_tokens_via_chrome_devtools() -> AuthTokens | None:
    """
    Extract auth tokens using Chrome DevTools.

    This function assumes Chrome DevTools MCP is available and connected
    to a Chrome browser. It will:
    1. Navigate to notebooklm.google.com
    2. Check if logged in
    3. If not, wait for user to log in
    4. Extract cookies and CSRF token

    Returns:
        AuthTokens if successful, None otherwise
    """
    # This is a placeholder - the actual implementation would use
    # Chrome DevTools MCP tools. Since we're inside an MCP server,
    # we can't directly call another MCP's tools.
    #
    # Instead, we'll provide a CLI command that can be run separately
    # to extract and cache the tokens.

    raise NotImplementedError(
        "Direct Chrome DevTools extraction not implemented. "
        "Use the 'nlm login' CLI command instead."
    )


def extract_csrf_from_page_source(html: str) -> str | None:
    """Extract CSRF token from page HTML.

    The token is stored in WIZ_global_data.SNlM0e or similar structures.
    """
    import re

    # Try different patterns for CSRF token
    patterns = [
        r'"SNlM0e":"([^"]+)"',  # WIZ_global_data.SNlM0e
        r'at=([^&"]+)',  # Direct at= value
        r'"FdrFJe":"([^"]+)"',  # Alternative location
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return None


def extract_session_id_from_page(html: str) -> str | None:
    """Extract session ID from page HTML."""
    import re

    patterns = [
        r'"FdrFJe":"([^"]+)"',
        r"f\.sid=(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return None


# ============================================================================
# CLI Authentication Flow
# ============================================================================
#
# This is designed to be run as a separate command before starting the MCP.
# It uses Chrome DevTools MCP interactively to extract auth tokens.
#
# Usage:
#   1. Make sure Chrome is open with DevTools MCP connected
#   2. Run: nlm login
#   3. If not logged in, log in via the Chrome window
#   4. Tokens are cached to ~/.notebooklm-mcp-cli/auth.json
#   5. Start the MCP server - it will use cached tokens
#
# The auth flow script is separate because:
# - MCP servers can't easily call other MCP tools
# - Interactive login needs user attention
# - Caching allows the MCP to start without browser interaction


def parse_cookies_from_chrome_format(cookies_list: list[dict]) -> dict[str, str]:
    """Parse cookies from Chrome DevTools format to simple dict."""
    result = {}
    for cookie in cookies_list:
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        if name:
            result[name] = value
    return result


# Tokens that need to be present for auth to work
REQUIRED_COOKIES = ["SID", "HSID", "SSID", "APISID", "SAPISID"]


def validate_cookies(cookies: dict[str, str]) -> bool:
    """Check if required cookies are present."""
    return all(required in cookies for required in REQUIRED_COOKIES)


# =============================================================================
# Multi-Profile Authentication (for CLI)
# =============================================================================


class Profile:
    """Represents an authentication profile (for CLI multi-account support)."""

    def __init__(
        self,
        name: str,
        cookies: list[dict] | dict[str, str],
        csrf_token: str | None = None,
        session_id: str | None = None,
        email: str | None = None,
        last_validated: Any = None,
        build_label: str | None = None,
    ) -> None:
        self.name = name
        self.cookies = cookies
        self.csrf_token = csrf_token
        self.session_id = session_id
        self.email = email
        self.last_validated = last_validated
        self.build_label = build_label

    def to_dict(self) -> dict:
        """Convert profile to dictionary for serialization."""
        return {
            "name": self.name,
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "session_id": self.session_id,
            "email": self.email,
            "build_label": self.build_label,
            "last_validated": (self.last_validated.isoformat() if self.last_validated else None),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Create profile from dictionary."""
        from datetime import datetime

        last_validated = None
        if data.get("last_validated"):
            with contextlib.suppress(ValueError, TypeError):
                last_validated = datetime.fromisoformat(data["last_validated"])

        return cls(
            name=data.get("name", "default"),
            cookies=(
                data.get("cookies", [])
                if isinstance(data.get("cookies"), list)
                else data.get("cookies", {})
            ),
            csrf_token=data.get("csrf_token"),
            session_id=data.get("session_id"),
            email=data.get("email"),
            last_validated=last_validated,
        )


class AuthManager:
    """Manages authentication profiles and credentials (for CLI multi-account support)."""

    def __init__(self, profile_name: str = "default") -> None:
        self.profile_name = profile_name
        self._profile: Profile | None = None

    @property
    def profile_dir(self) -> Path:
        """Get the directory for the current profile."""
        from notebooklm_tools.utils.config import get_profile_dir

        return get_profile_dir(self.profile_name)

    @property
    def cookies_file(self) -> Path:
        """Get the cookies file path."""
        return self.profile_dir / "cookies.json"

    @property
    def metadata_file(self) -> Path:
        """Get the metadata file path."""
        return self.profile_dir / "metadata.json"

    def profile_exists(self) -> bool:
        """Check if the profile exists."""
        return self.cookies_file.exists()

    def load_profile(self, force_reload: bool = False) -> Profile:
        """Load the current profile from disk."""
        from datetime import datetime

        from notebooklm_tools.core.exceptions import (
            AuthenticationError,
            ProfileNotFoundError,
        )

        if self._profile is not None and not force_reload:
            return self._profile

        if not self.profile_exists():
            raise ProfileNotFoundError(self.profile_name)

        try:
            cookies = json.loads(self.cookies_file.read_text(encoding="utf-8"))
            metadata = {}
            if self.metadata_file.exists():
                metadata = json.loads(self.metadata_file.read_text(encoding="utf-8"))

            self._profile = Profile(
                name=self.profile_name,
                cookies=cookies,
                csrf_token=metadata.get("csrf_token"),
                session_id=metadata.get("session_id"),
                email=metadata.get("email"),
                last_validated=(
                    datetime.fromisoformat(metadata["last_validated"])
                    if metadata.get("last_validated")
                    else None
                ),
                build_label=metadata.get("build_label"),
            )
            return self._profile
        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to load profile '{self.profile_name}': {e}",
                hint="The profile may be corrupted. Try 'nlm login' to re-authenticate.",
            ) from e

    def save_profile(
        self,
        cookies: list[dict] | dict[str, str],
        csrf_token: str | None = None,
        session_id: str | None = None,
        email: str | None = None,
        force: bool = False,
        build_label: str | None = None,
    ) -> Profile:
        """Save credentials to the current profile.

        Raises:
            AccountMismatchError: If the profile already has credentials for a
                different email and force is False.
        """
        from datetime import datetime

        from notebooklm_tools.core.exceptions import AccountMismatchError

        # Guard: check for account mismatch before overwriting
        if not force and email and self.metadata_file.exists():
            try:
                existing_metadata = json.loads(self.metadata_file.read_text(encoding="utf-8"))
                stored_email = existing_metadata.get("email")
                if stored_email and stored_email != email:
                    raise AccountMismatchError(
                        stored_email=stored_email,
                        new_email=email,
                        profile_name=self.profile_name,
                    )
            except (json.JSONDecodeError, KeyError):
                pass  # Corrupted metadata, allow overwrite

        from notebooklm_tools.utils.config import safe_mkdir

        safe_mkdir(self.profile_dir, parents=True)

        # Set restrictive permissions on the directory
        self.profile_dir.chmod(0o700)

        # Save cookies with restrictive permissions from creation
        fd = os.open(str(self.cookies_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            f = os.fdopen(fd, "w", encoding="utf-8")
        except BaseException:
            os.close(fd)
            raise
        with f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        # Save metadata with restrictive permissions from creation
        metadata = {
            "csrf_token": csrf_token,
            "session_id": session_id,
            "email": email,
            "build_label": build_label,
            "last_validated": datetime.now().isoformat(),
        }
        fd = os.open(str(self.metadata_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            f = os.fdopen(fd, "w", encoding="utf-8")
        except BaseException:
            os.close(fd)
            raise
        with f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self._profile = Profile(
            name=self.profile_name,
            cookies=cookies,
            csrf_token=csrf_token,
            session_id=session_id,
            email=email,
            last_validated=datetime.now(),
            build_label=build_label,
        )
        return self._profile

    def delete_profile(self) -> None:
        """Delete the current profile."""
        import shutil

        from notebooklm_tools.utils.config import get_profiles_dir

        # Get path directly without auto-creating (profile_dir property auto-creates)
        profile_path = get_profiles_dir() / self.profile_name
        if profile_path.exists():
            shutil.rmtree(profile_path)
        self._profile = None

    def get_cookies(self) -> dict[str, str]:
        """Get cookies for the current profile as simple dict."""
        profile = self.load_profile()
        if isinstance(profile.cookies, list):
            # Convert list[dict] to dict[str, str]
            return {c["name"]: c["value"] for c in profile.cookies if "name" in c and "value" in c}
        return profile.cookies

    def get_raw_cookies(self) -> list[dict] | dict[str, str]:
        """Get raw cookies (list or dict)."""
        profile = self.load_profile()
        return profile.cookies

    def get_cookie_header(self) -> str:
        """Get Cookie header value for HTTP requests."""
        from notebooklm_tools.utils.browser import cookies_to_header

        return cookies_to_header(self.get_cookies())

    def get_headers(self) -> dict[str, str]:
        """Get headers for NotebookLM API requests."""
        from notebooklm_tools.utils.browser import cookies_to_header

        profile = self.load_profile()
        headers = {
            "Cookie": cookies_to_header(profile.cookies),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": get_base_url(),
            "Referer": f"{get_base_url()}/",
        }
        if profile.csrf_token:
            headers["X-Goog-Csrf-Token"] = profile.csrf_token
        return headers

    def check_validity(self, *, live: bool = True, timeout: float = 12.0) -> "AuthCheckResult":
        """Check the validity of the current profile's credentials."""
        return check_auth(profile=self.profile_name, live=live, timeout=timeout)

    @staticmethod
    def list_profiles() -> list[str]:
        """List all available profiles."""
        from notebooklm_tools.utils.config import get_profiles_dir

        profiles_dir = get_profiles_dir()
        if not profiles_dir.exists():
            return []
        return [d.name for d in profiles_dir.iterdir() if d.is_dir()]

    def login_with_file(self, file_path: str | Path) -> Profile:
        """Parse cookies from file and save to profile."""
        from notebooklm_tools.core.exceptions import AuthenticationError
        from notebooklm_tools.utils.browser import (
            parse_cookies_from_file,
            validate_notebooklm_cookies,
        )

        cookies = parse_cookies_from_file(file_path)

        if not validate_notebooklm_cookies(cookies):
            raise AuthenticationError(
                message="Parsed cookies don't appear to be valid for NotebookLM",
                hint="Make sure the file contains cookies from a NotebookLM session.",
            )

        return self.save_profile(cookies)


def get_auth_manager(profile: str | None = None) -> AuthManager:
    """Get an AuthManager for the specified or default profile."""
    from notebooklm_tools.utils.config import get_config

    if profile is None:
        profile = get_config().auth.default_profile

    return AuthManager(profile)


# =============================================================================
# Elegant Unified Auth Validity Check (the single source of truth)
# =============================================================================


@dataclass
class AuthCheckResult:
    """Result of an authentication validity check.

    This is the canonical return type for all "am I still logged in?"
    questions in the system (CLI --check, MCP server_info, doctor, etc.).
    """

    valid: bool
    reason: str | None = None  # "no_tokens", "expired", "network_error", etc.
    checked_at: float = field(default_factory=time.time)
    live: bool = True
    profile: str = "default"
    details: dict[str, Any] | None = None  # e.g. extracted csrf on success


# Browser-like headers required for the NotebookLM homepage fetch.
# These match _PAGE_FETCH_HEADERS in BaseClient (core/base.py).
# The Sec-Fetch-* headers are critical: without them Google may redirect
# even valid cookies to the login page, causing false "expired" results.
_PAGE_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def _fetch_notebooklm_homepage(
    cookies: dict[str, str] | list[dict],
    *,
    timeout: float = 12.0,
    base_url: str | None = None,
):
    """Minimal, isolated homepage fetch used for the live auth check.

    Returns the final response after redirects. Callers decide what the
    final URL / status means.

    Note: uses proper browser-like _PAGE_FETCH_HEADERS (including Sec-Fetch-*)
    to avoid false redirects to Google login that occur with minimal headers.
    """
    import httpx

    from notebooklm_tools.utils.browser import cookies_to_header

    if isinstance(cookies, list):
        cookie_dict = {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}
    else:
        cookie_dict = cookies

    headers = _PAGE_FETCH_HEADERS.copy()

    cookie_header = cookies_to_header(cookie_dict)
    if cookie_header:
        headers["Cookie"] = cookie_header

    url = base_url or get_base_url()

    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        return client.get(f"{url}/")


def check_auth(
    profile: str | None = None,
    *,
    live: bool = True,
    timeout: float = 12.0,
) -> AuthCheckResult:
    """Single source of truth for whether NotebookLM credentials are valid.

    This is the elegant root fix for the long-standing inconsistency between
    `nlm login --check` (live) and `server_info` (pure heuristic).

    live=True  → performs the authoritative minimal network check (homepage
                 fetch + Google login redirect detection). This is what
                 users and the MCP should trust.
    live=False → fast path based only on on-disk metadata (last_validated /
                 extracted_at). Useful for very hot paths.

    Returns an AuthCheckResult that both CLI and MCP code can render.
    """
    if profile is None:
        from notebooklm_tools.utils.config import get_config

        profile = get_config().auth.default_profile

    manager = AuthManager(profile)

    # Fast path: no profile at all
    if not manager.profile_exists():
        return AuthCheckResult(
            valid=False,
            reason="no_tokens",
            live=live,
            profile=profile,
        )

    try:
        p = manager.load_profile()
    except Exception as e:
        return AuthCheckResult(
            valid=False,
            reason=f"load_error: {e}",
            live=live,
            profile=profile,
        )

    # Convert to simple dict for the fetch helper
    if isinstance(p.cookies, list):
        cookie_dict = {c["name"]: c["value"] for c in p.cookies if "name" in c and "value" in c}
    else:
        cookie_dict = p.cookies

    if not cookie_dict:
        return AuthCheckResult(valid=False, reason="no_tokens", live=live, profile=profile)

    if not live:
        # Pure heuristic based on last successful validation
        if p.last_validated:
            # Consider anything validated in the last 7 days as good for the
            # non-live path (same spirit as the old 168h rule).
            age = (time.time() - p.last_validated.timestamp()) / 3600
            if age <= 168:
                return AuthCheckResult(
                    valid=True,
                    live=False,
                    profile=profile,
                    checked_at=p.last_validated.timestamp(),
                )
        return AuthCheckResult(valid=False, reason="stale_heuristic", live=False, profile=profile)

    # === Live authoritative path ===
    try:
        resp = _fetch_notebooklm_homepage(cookie_dict, timeout=timeout)

        final_url = str(resp.url)

        if "accounts.google.com" in final_url:
            return AuthCheckResult(
                valid=False,
                reason="expired",
                live=True,
                profile=profile,
                details={"final_url": final_url},
            )

        if resp.status_code != 200:
            return AuthCheckResult(
                valid=False,
                reason=f"http_{resp.status_code}",
                live=True,
                profile=profile,
            )

        # Try to extract fresh CSRF while we're here (nice side-effect)
        csrf = extract_csrf_from_page_source(resp.text) or ""

        # Update last_validated so that future non-live checks are accurate
        manager.save_profile(
            cookies=p.cookies,
            csrf_token=csrf or p.csrf_token,
            session_id=p.session_id,
            email=p.email,
            build_label=p.build_label,
        )

        return AuthCheckResult(
            valid=True,
            reason=None,
            live=True,
            profile=profile,
            details={"csrf_token": csrf} if csrf else None,
        )

    except Exception as exc:
        # Network / timeout / etc. — be conservative but do not lie.
        # We still have the cookies on disk; caller can decide.
        return AuthCheckResult(
            valid=False,
            reason=f"network_error: {type(exc).__name__}",
            live=True,
            profile=profile,
            details={"exception": str(exc)},
        )


# =============================================================================
# AuthHealthChecker — multi-probe health check with caching
# =============================================================================


@dataclass
class AuthProbeResult:
    """Result from a single health probe (homepage or API).

    Each probe records its own endpoint, latency, and error for
    detailed diagnostics.
    """

    probe: str  # "homepage" or "api"
    valid: bool
    status_code: int | None = None
    latency_ms: float = 0.0
    error: str | None = None
    detail: str | None = None


@dataclass
class AuthHealthReport:
    """Full diagnostic report from AuthHealthChecker.

    Contains all probe results, the final verdict, and timing info
    so callers (server_info, doctor, CLI --check) can render either
    a simple status string or a detailed breakdown.
    """

    valid: bool
    status: str  # "configured" | "stale" | "unverified" | "not_configured"
    probes: list[AuthProbeResult]
    token_age_hours: float | None = None
    profile: str = "default"
    checked_at: float = 0.0
    cached: bool = False


class AuthHealthChecker:
    """Professional auth health checker with multi-probe strategy and caching.

    **Probe strategy (tried in order):**

    1. **Homepage** (``check_auth(live=True)``) — fast, catches clear expiry.
    2. **API** — creates a ``NotebookLMClient`` and lists notebooks with
       ``pageSize=1``.  Only attempted when the homepage probe returns
       a redirect to Google login ("expired").  This accounts for the
       fact that the homepage and the RPC API endpoint may treat the
       same cookies differently.

    **Caching:**

    Results are cached for 30 seconds (``CACHE_TTL``).  The cache is
    invalidated when any auth file on disk changes (detected via
    ``get_active_auth_mtime()``), so an external ``nlm login`` is
    picked up instantly.

    **Diagnostics:**

    Every check returns an ``AuthHealthReport`` with per-probe details
    (endpoint, status code, latency, error) so callers can render
    a meaningful diagnostic message instead of a cryptic status label.
    """

    CACHE_TTL: float = 30.0

    def __init__(self, profile: str | None = None) -> None:
        self._profile = profile
        self._report: AuthHealthReport | None = None
        self._cache_ts: float = 0.0
        self._auth_mtime: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, *, force: bool = False, timeout: float = 12.0) -> AuthHealthReport:
        """Return a cached or fresh health report.

        Args:
            force: If True, bypass the cache and run all probes.
            timeout: Timeout in seconds for each HTTP probe.

        Returns:
            An ``AuthHealthReport`` with the final verdict and per-probe details.
        """
        now = time.time()

        if not force and self._report is not None:
            age = now - self._cache_ts
            if age < self.CACHE_TTL:
                current_mtime = self._get_auth_mtime()
                if current_mtime == self._auth_mtime:
                    return replace(self._report, cached=True)

        report = self._run_checks(timeout=timeout)

        self._report = report
        self._cache_ts = now
        self._auth_mtime = self._get_auth_mtime()
        return report

    def invalidate(self) -> None:
        """Force the next ``check()`` call to re-run all probes."""
        self._report = None
        self._cache_ts = 0.0

    # ------------------------------------------------------------------
    # Probe orchestration
    # ------------------------------------------------------------------

    def _run_checks(self, *, timeout: float = 12.0) -> AuthHealthReport:
        probes: list[AuthProbeResult] = []

        # Phase 1: Resolve the auth profile
        resolved_profile = self._profile
        if resolved_profile is None:
            from notebooklm_tools.utils.config import get_config

            resolved_profile = get_config().auth.default_profile

        manager = AuthManager(resolved_profile)

        if not manager.profile_exists():
            return AuthHealthReport(
                valid=False,
                status="not_configured",
                probes=[],
                profile=resolved_profile,
                checked_at=time.time(),
            )

        try:
            profile = manager.load_profile()
            cookie_dict = self._cookies_to_dict(profile)
        except Exception as e:
            return AuthHealthReport(
                valid=False,
                status="stale",
                probes=[AuthProbeResult(probe="load", valid=False, error=str(e))],
                profile=resolved_profile,
                checked_at=time.time(),
            )

        if not cookie_dict:
            return AuthHealthReport(
                valid=False,
                status="not_configured",
                probes=[],
                profile=resolved_profile,
                checked_at=time.time(),
            )

        token_age = self._compute_token_age(profile)

        # Phase 2: Probe 1 — homepage fetch
        hp_start = time.perf_counter()
        hp_valid, hp_reason, hp_detail, hp_code = self._probe_homepage(cookie_dict, timeout=timeout)
        hp_latency = (time.perf_counter() - hp_start) * 1000

        if hp_reason is None:  # homepage succeeded
            probes.append(
                AuthProbeResult(
                    probe="homepage",
                    valid=True,
                    status_code=hp_code,
                    latency_ms=hp_latency,
                )
            )
            self._update_profile_on_success(manager, profile, hp_detail)
            return AuthHealthReport(
                valid=True,
                status="configured",
                probes=probes,
                token_age_hours=token_age,
                profile=resolved_profile,
                checked_at=time.time(),
            )

        probes.append(
            AuthProbeResult(
                probe="homepage",
                valid=False,
                status_code=hp_code,
                latency_ms=hp_latency,
                error=hp_reason,
                detail=hp_detail,
            )
        )

        # Phase 3: Probe 2 — lightweight API call (only when homepage redirects
        # to login or rejects auth, which is the most common false-positive scenario)
        if hp_reason in ("expired", "http_401", "http_403"):
            api_start = time.perf_counter()
            api_valid, api_error = self._probe_api(cookie_dict, profile.csrf_token, timeout=timeout)
            api_latency = (time.perf_counter() - api_start) * 1000

            if api_valid:
                probes.append(
                    AuthProbeResult(
                        probe="api",
                        valid=True,
                        latency_ms=api_latency,
                        detail="Homepage rejected auth but API succeeded (false positive avoided).",
                    )
                )
                self._update_profile_on_success(manager, profile)
                return AuthHealthReport(
                    valid=True,
                    status="configured",
                    probes=probes,
                    token_age_hours=token_age,
                    profile=resolved_profile,
                    checked_at=time.time(),
                )

            probes.append(
                AuthProbeResult(
                    probe="api",
                    valid=False,
                    error=api_error or "unknown",
                    latency_ms=api_latency,
                )
            )

        # Phase 4: Determine final verdict from all probe results
        verdict = self._determine_verdict(probes)
        return AuthHealthReport(
            valid=verdict != "configured",
            status=verdict,
            probes=probes,
            token_age_hours=token_age,
            profile=resolved_profile,
            checked_at=time.time(),
        )

    # ------------------------------------------------------------------
    # Individual probes
    # ------------------------------------------------------------------

    def _probe_homepage(
        self, cookie_dict: dict[str, str], *, timeout: float
    ) -> tuple[bool, str | None, str | None, int | None]:
        """Fetch the NotebookLM homepage.

        Returns (valid, reason, detail, status_code).
        reason is None when the homepage check passes.
        """
        try:
            resp = _fetch_notebooklm_homepage(cookie_dict, timeout=timeout)
            final_url = str(resp.url)

            if "accounts.google.com" in final_url:
                return False, "expired", final_url, resp.status_code
            if resp.status_code != 200:
                return False, f"http_{resp.status_code}", None, resp.status_code

            csrf = extract_csrf_from_page_source(resp.text) or ""
            return True, None, csrf, resp.status_code

        except Exception as e:
            return False, f"network_error: {type(e).__name__}", str(e), None

    def _probe_api(
        self, cookie_dict: dict[str, str], csrf_token: str | None, *, timeout: float
    ) -> tuple[bool, str | None]:
        """Lightweight API probe: create a NotebookLMClient and list notebooks.

        Returns (valid, error_message_or_None).

        This is only called as a fallback when the homepage check looks
        expired.  The API endpoint often accepts cookies that the homepage
        rejects due to missing request headers.
        """
        try:
            from notebooklm_tools.core.client import NotebookLMClient

            client = NotebookLMClient(cookies=cookie_dict, csrf_token=csrf_token or "")
            client.list_notebooks()
            return True, None
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cookies_to_dict(profile: Any) -> dict[str, str]:
        """Convert profile cookies to a plain dict."""
        if isinstance(profile.cookies, list):
            return {c["name"]: c["value"] for c in profile.cookies if "name" in c and "value" in c}
        if isinstance(profile.cookies, dict):
            return profile.cookies
        return {}

    @staticmethod
    def _compute_token_age(profile: Any) -> float | None:
        """Return token age in hours, or None if unknown."""
        if profile.last_validated is None:
            return None
        try:
            return float((time.time() - profile.last_validated.timestamp()) / 3600)
        except Exception:
            return None

    @staticmethod
    def _get_auth_mtime() -> float:
        """Return the mtime of the most recently modified auth file."""
        try:
            from notebooklm_tools.services.auth import get_active_auth_mtime

            return get_active_auth_mtime()
        except Exception:
            return 0.0

    @staticmethod
    def _update_profile_on_success(
        manager: AuthManager, profile: Any, csrf_token: str | None = None
    ) -> None:
        """Persist fresh CSRF and update last_validated after a successful check."""
        try:
            manager.save_profile(
                cookies=profile.cookies,
                csrf_token=csrf_token or profile.csrf_token,
                session_id=profile.session_id,
                email=profile.email,
                build_label=profile.build_label,
            )
        except Exception as e:
            logger.debug(f"Failed to update profile on successful auth check: {e}")

    @staticmethod
    def _determine_verdict(probes: list[AuthProbeResult]) -> str:
        """Aggregate probe results into a final verdict.

        Prioritisation:
        - Any network error across ALL probes → "unverified"
        - Homepage expired + API also failed → "stale"
        - Any other auth failure → "stale"
        - All probes unreachable → "unverified"
        """
        if not probes:
            return "not_configured"

        has_auth_failure = any(p.error and not p.error.startswith("network_error:") for p in probes)
        has_network_error = any(p.error and p.error.startswith("network_error:") for p in probes)
        all_network_errors = all(p.error and p.error.startswith("network_error:") for p in probes)

        if all_network_errors:
            return "unverified"
        if has_auth_failure:
            return "stale"
        if has_network_error:
            return "unverified"
        return "stale"  # conservative fallback
