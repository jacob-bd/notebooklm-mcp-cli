"""Auth tools - Authentication management."""

import time
import urllib.parse
from typing import Any

from ._utils import get_client, reset_client, logged_tool, ESSENTIAL_COOKIES


@logged_tool()
def refresh_auth() -> dict[str, Any]:
    """Reload auth tokens from disk or run headless re-authentication.

    Call this after running `nlm login` to pick up new tokens,
    or to attempt automatic re-authentication if Chrome profile has saved login.

    Returns status indicating if tokens were refreshed successfully.
    """
    try:
        # Try reloading from disk first
        from notebooklm_tools.core.auth import load_cached_tokens

        cached = load_cached_tokens()
        if cached:
            # Reset client to force re-initialization with fresh tokens
            reset_client()
            get_client()  # This will use the cached tokens
            return {
                "status": "success",
                "message": "Auth tokens reloaded from disk cache.",
            }

        # Try headless auth if Chrome profile exists
        try:
            from notebooklm_tools.utils.cdp import run_headless_auth

            tokens = run_headless_auth()
            if tokens:
                reset_client()
                get_client()
                return {
                    "status": "success",
                    "message": "Auth tokens refreshed via headless Chrome.",
                }
        except Exception:
            pass

        return {
            "status": "error",
            "error": "No cached tokens found. Run 'nlm login' to authenticate.",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@logged_tool()
def save_auth_tokens(
    cookies: str,
    csrf_token: str = "",
    session_id: str = "",
    request_body: str = "",
    request_url: str = "",
) -> dict[str, Any]:
    """Save NotebookLM cookies (FALLBACK method - try `nlm login` first!).

    IMPORTANT FOR AI ASSISTANTS:
    - First, run `nlm login` via Bash/terminal (automated, preferred)
    - Only use this tool if the automated CLI fails

    Args:
        cookies: Cookie header from Chrome DevTools (only needed if CLI fails)
        csrf_token: Deprecated - auto-extracted
        session_id: Deprecated - auto-extracted
        request_body: Optional - contains CSRF if extracting manually
        request_url: Optional - contains session ID if extracting manually
    """
    try:
        from notebooklm_tools.core.auth import AuthTokens, save_tokens_to_cache, get_cache_path

        # Parse cookie string to dict
        all_cookies = {}
        for part in cookies.split("; "):
            if "=" in part:
                key, value = part.split("=", 1)
                all_cookies[key] = value

        # Validate required cookies
        required = ["SID", "HSID", "SSID", "APISID", "SAPISID"]
        missing = [c for c in required if c not in all_cookies]
        if missing:
            return {
                "status": "error",
                "error": f"Missing required cookies: {missing}",
            }

        # Filter to only essential cookies
        cookie_dict = {k: v for k, v in all_cookies.items() if k in ESSENTIAL_COOKIES}

        # Try to extract CSRF token from request body if provided
        if not csrf_token and request_body:
            if "at=" in request_body:
                at_part = request_body.split("at=")[1].split("&")[0]
                csrf_token = urllib.parse.unquote(at_part)

        # Try to extract session ID from request URL if provided
        if not session_id and request_url:
            if "f.sid=" in request_url:
                sid_part = request_url.split("f.sid=")[1].split("&")[0]
                session_id = urllib.parse.unquote(sid_part)

        # Try to extract build label from request URL if provided
        build_label = ""
        if request_url and "bl=" in request_url:
            bl_part = request_url.split("bl=")[1].split("&")[0]
            build_label = urllib.parse.unquote(bl_part)

        # Create and save tokens
        tokens = AuthTokens(
            cookies=cookie_dict,
            csrf_token=csrf_token,
            session_id=session_id,
            build_label=build_label,
            extracted_at=time.time(),
        )
        save_tokens_to_cache(tokens)

        # Reset client so next call uses fresh tokens
        reset_client()

        # Build status message
        if csrf_token and session_id:
            token_msg = "CSRF token and session ID extracted from network request - no page fetch needed! ⚡"
        elif csrf_token:
            token_msg = "CSRF token extracted from network request. Session ID will be auto-extracted on first use."
        elif session_id:
            token_msg = "Session ID extracted from network request. CSRF token will be auto-extracted on first use."
        else:
            token_msg = "CSRF token and session ID will be auto-extracted on first API call (~1-2s one-time delay)."

        return {
            "status": "success",
            "message": f"Saved {len(cookie_dict)} essential cookies (filtered from {len(all_cookies)}). {token_msg}",
            "cache_path": str(get_cache_path()),
            "extracted_csrf": bool(csrf_token),
            "extracted_session_id": bool(session_id),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
