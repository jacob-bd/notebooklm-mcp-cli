"""Authentication helper for NotebookLM MCP CLI.

Uses Chrome DevTools MCP to extract auth tokens from an authenticated browser session.
If the user is not logged in, prompts them to log in via the Chrome window.

Storage location: ~/.notebooklm-mcp-cli/ (unified for CLI and MCP)
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuthTokens:
    """Authentication tokens for NotebookLM.

    Only cookies are required. CSRF token and session ID are optional because
    they can be auto-extracted from the NotebookLM page when needed.
    """
    cookies: dict[str, str]
    csrf_token: str = ""  # Optional - auto-extracted from page
    session_id: str = ""  # Optional - auto-extracted from page
    extracted_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "session_id": self.session_id,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthTokens":
        return cls(
            cookies=data["cookies"],
            csrf_token=data.get("csrf_token", ""),  # May be empty
            session_id=data.get("session_id", ""),  # May be empty
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
                extracted_at=profile.last_validated.timestamp() if profile.last_validated else time.time()
            )
    except Exception:
        pass

    # 2. Fallback to legacy auth cache
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            data = json.load(f)
        tokens = AuthTokens.from_dict(data)

        # Just warn if tokens are old, but still return them
        # Let the API client's functional check determine validity
        if tokens.is_expired():
            print("Note: Cached tokens are older than 1 week. They may still work.")

        return tokens
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Failed to load cached tokens: {e}")
        return None


def save_tokens_to_cache(tokens: AuthTokens, silent: bool = False) -> None:
    """Save tokens to cache.

    Args:
        tokens: AuthTokens to save
        silent: If True, don't print confirmation message (for auto-updates)
    """
    cache_path = get_cache_path()
    with open(cache_path, "w") as f:
        json.dump(tokens.to_dict(), f, indent=2)
    if not silent:
        print(f"Auth tokens cached to {cache_path}")


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
        "Use the 'notebooklm-mcp-auth' CLI command instead."
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
        r'f\.sid=(\d+)',
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
#   2. Run: notebooklm-mcp-auth
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
    for required in REQUIRED_COOKIES:
        if required not in cookies:
            return False
    return True


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
        last_validated: "datetime | None" = None,
    ) -> None:
        self.name = name
        self.cookies = cookies
        self.csrf_token = csrf_token
        self.session_id = session_id
        self.email = email
        self.last_validated = last_validated

    def to_dict(self) -> dict:
        """Convert profile to dictionary for serialization."""
        from datetime import datetime
        return {
            "name": self.name,
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "session_id": self.session_id,
            "email": self.email,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Create profile from dictionary."""
        from datetime import datetime
        last_validated = None
        if data.get("last_validated"):
            try:
                last_validated = datetime.fromisoformat(data["last_validated"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            name=data.get("name", "default"),
            cookies=data.get("cookies", []) if isinstance(data.get("cookies"), list) else data.get("cookies", {}),
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
        from notebooklm_tools.core.exceptions import AuthenticationError, ProfileNotFoundError
        
        if self._profile is not None and not force_reload:
            return self._profile
        
        if not self.profile_exists():
            raise ProfileNotFoundError(self.profile_name)
        
        try:
            cookies = json.loads(self.cookies_file.read_text())
            metadata = {}
            if self.metadata_file.exists():
                metadata = json.loads(self.metadata_file.read_text())
            
            self._profile = Profile(
                name=self.profile_name,
                cookies=cookies,
                csrf_token=metadata.get("csrf_token"),
                session_id=metadata.get("session_id"),
                email=metadata.get("email"),
                last_validated=datetime.fromisoformat(metadata["last_validated"])
                if metadata.get("last_validated") else None,
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
    ) -> Profile:
        """Save credentials to the current profile."""
        from datetime import datetime
        
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on the directory
        self.profile_dir.chmod(0o700)
        
        # Save cookies
        self.cookies_file.write_text(json.dumps(cookies, indent=2))
        self.cookies_file.chmod(0o600)
        
        # Save metadata
        metadata = {
            "csrf_token": csrf_token,
            "session_id": session_id,
            "email": email,
            "last_validated": datetime.now().isoformat(),
        }
        self.metadata_file.write_text(json.dumps(metadata, indent=2))
        self.metadata_file.chmod(0o600)
        
        self._profile = Profile(
            name=self.profile_name,
            cookies=cookies,
            csrf_token=csrf_token,
            session_id=session_id,
            email=email,
            last_validated=datetime.now(),
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
            "Origin": "https://notebooklm.google.com",
            "Referer": "https://notebooklm.google.com/",
        }
        if profile.csrf_token:
            headers["X-Goog-Csrf-Token"] = profile.csrf_token
        return headers

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
        from notebooklm_tools.utils.browser import parse_cookies_from_file, validate_notebooklm_cookies
        from notebooklm_tools.core.exceptions import AuthenticationError
        
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
