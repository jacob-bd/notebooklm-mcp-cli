"""Chrome DevTools Protocol (CDP) utilities for cookie extraction.

This module provides a keychain-free way to extract cookies from Chrome
by using the Chrome DevTools Protocol over WebSocket.

Usage:
    1. Chrome is launched with --remote-debugging-port
    2. We connect via WebSocket and use Network.getCookies
    3. No keychain access required!
"""

import json
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from httpx import Client
httpx_client = Client()
import websocket

_cached_ws: websocket.WebSocket | None = None
_cached_ws_url: str | None = None

from notebooklm_tools.core.exceptions import AuthenticationError


CDP_DEFAULT_PORT = 9222
CDP_PORT_RANGE = range(9222, 9232)  # Ports to scan for existing/available
NOTEBOOKLM_URL = "https://notebooklm.google.com/"


def normalize_cdp_http_url(cdp_url: str) -> str:
    """Normalize a CDP endpoint into an HTTP base URL.

    Accepts:
      - http://127.0.0.1:18800
      - ws://127.0.0.1:18800/devtools/browser/<id>
      - 127.0.0.1:18800
      - 18800
    """
    raw = (cdp_url or "").strip()
    if not raw:
        raise ValueError("cdp_url is required")

    # Bare port shorthand
    if raw.isdigit():
        return f"http://127.0.0.1:{raw}"

    if raw.startswith(("ws://", "wss://")):
        parsed = urlparse(raw)
        if not parsed.hostname or not parsed.port:
            raise ValueError(f"Invalid CDP websocket URL: {cdp_url}")
        scheme = "https" if parsed.scheme == "wss" else "http"
        return f"{scheme}://{parsed.hostname}:{parsed.port}"

    if raw.startswith(("http://", "https://")):
        return raw.rstrip("/")

    # host:port
    return f"http://{raw.rstrip('/')}"


def find_available_port(starting_from: int = 9222, max_attempts: int = 10) -> int:
    """Find an available port for Chrome debugging.
    
    Args:
        starting_from: Port to start scanning from
        max_attempts: Number of ports to try
    
    Returns:
        An available port number
    
    Raises:
        RuntimeError: If no available ports found
    """
    import socket
    for offset in range(max_attempts):
        port = starting_from + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No available ports in range {starting_from}-{starting_from + max_attempts - 1}. "
        "Close some applications and try again."
    )


def get_chrome_path() -> str | None:
    """Get the Chrome executable path for the current platform."""
    system = platform.system()
    
    if system == "Darwin":
        path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        return path if Path(path).exists() else None
    elif system == "Linux":
        candidates = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
        return None
    elif system == "Windows":
        path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        return path if Path(path).exists() else None
    
    return None


# Import Chrome profile directory from unified config
from notebooklm_tools.utils.config import get_chrome_profile_dir


def is_profile_locked(profile_name: str = "default") -> bool:
    """Check if the Chrome profile is locked (Chrome is using it)."""
    lock_file = get_chrome_profile_dir(profile_name) / "SingletonLock"
    return lock_file.exists()


def find_existing_nlm_chrome(port_range: range = CDP_PORT_RANGE) -> tuple[int | None, str | None]:
    """Find an existing NLM Chrome instance on any port in range.
    
    Scans the port range looking for a Chrome DevTools endpoint.
    This allows reconnecting to an existing auth Chrome window.
    
    Returns:
        The port number and debugger URL if found, (None, None) otherwise
    """
    import socket
    for port in port_range:
        # First check if the port is in use. If `bind` succeeds, the port is unused, 
        # meaning Chrome is NOT listening there. This avoids a 2-second timeout 
        # on OSes that drop packets instead of actively refusing connection.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                # Port is available (not in use), so move to the next one
                continue
        except OSError:
            # Port is in use, let's see if it's a Chrome DevTools endpoint
            pass

        debugger_url = get_debugger_url(port, timeout=2)
        if debugger_url:
            return port, debugger_url
    return None, None


def launch_chrome_process(port: int = CDP_DEFAULT_PORT, headless: bool = False, profile_name: str = "default") -> subprocess.Popen | None:
    """Launch Chrome and return process handle."""
    chrome_path = get_chrome_path()
    if not chrome_path:
        return None
    
    profile_dir = get_chrome_profile_dir(profile_name)
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profile_dir}",
        "--remote-allow-origins=*",
    ]
    
    if headless:
        args.append("--headless=new")
    
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return process
    except Exception:
        return None


# Module-level Chrome state for termination and reconnection
_chrome_process: subprocess.Popen | None = None
_chrome_port: int | None = None


def launch_chrome(port: int = CDP_DEFAULT_PORT, headless: bool = False, profile_name: str = "default") -> bool:
    """Launch Chrome with remote debugging enabled."""
    global _chrome_process, _chrome_port
    _chrome_process = launch_chrome_process(port, headless, profile_name)
    _chrome_port = port if _chrome_process else None
    return _chrome_process is not None


def terminate_chrome(process: subprocess.Popen | None = None, port: int | None = None) -> bool:
    """Terminate the Chrome process launched by this module.
    
    This releases the profile lock so headless auth can work later.
    
    Returns:
        True if Chrome was terminated, False if no process to terminate.
    """
    global _chrome_process, _chrome_port, _cached_ws, _cached_ws_url
    process = process or _chrome_process
    port = port or _chrome_port
    if process is None:
        return False

    # Attempt graceful shutdown via CDP to prevent "Restore Pages" warnings on next launch
    try:
        if port or _cached_ws_url:
            execute_cdp_command(_cached_ws_url or get_debugger_url(_chrome_port), "Browser.close")
            _cached_ws.close()
        else:
            # No fast path, use slow path
            process.terminate()
    except Exception:
        pass # Ignore connection drops or failures during close

    _cached_ws = _cached_ws_url = None

    try:
        # Wait up to 5 seconds for the graceful shutdown to finish
        process.wait(timeout=5)
    except Exception:
        # If it didn't close in time, force terminate
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    if process == _chrome_process:
        _chrome_process = None
        _chrome_port = None
    return True


def get_debugger_url(port: int = CDP_DEFAULT_PORT, *, tries: int = 1, timeout: int = 5) -> str | None:
    """Get the WebSocket debugger URL for Chrome."""
    for attempt in range(tries):
        try:
            response = httpx_client.get(f"http://localhost:{port}/json/version", timeout=timeout)
            data = response.json()
            return data.get("webSocketDebuggerUrl")
        except Exception:
            # Don't sleep on the last try
            if attempt < tries - 1:
                time.sleep(1)
    return None


def get_pages_by_cdp_url(cdp_http_url: str) -> list[dict]:
    """Get list of open pages from an arbitrary CDP HTTP endpoint."""
    try:
        response = httpx_client.get(f"{cdp_http_url}/json", timeout=5)
        return response.json()
    except Exception:
        return []


def find_or_create_notebooklm_page_by_cdp_url(cdp_http_url: str) -> dict | None:
    """Find an existing NotebookLM page or create one on a given CDP endpoint."""
    pages = get_pages_by_cdp_url(cdp_http_url)

    for page in pages:
        url = page.get("url", "")
        if "notebooklm.google.com" in url:
            return page

    try:
        encoded_url = quote(NOTEBOOKLM_URL, safe="")
        response = httpx_client.put(
            f"{cdp_http_url}/json/new?{encoded_url}",
            timeout=15,
        )
        if response.status_code == 200 and response.text.strip():
            return response.json()

        # Fallback: create blank page then navigate
        response = httpx_client.put(f"{cdp_http_url}/json/new", timeout=10)
        if response.status_code == 200 and response.text.strip():
            page = response.json()
            ws_url = page.get("webSocketDebuggerUrl")
            if ws_url:
                navigate_to_url(ws_url, NOTEBOOKLM_URL)
            return page

        return None
    except Exception:
        return None


def find_or_create_notebooklm_page(port: int = CDP_DEFAULT_PORT) -> dict | None:
    """Find an existing NotebookLM page or create a new one."""
    return find_or_create_notebooklm_page_by_cdp_url(f"http://localhost:{port}")

def execute_cdp_command(ws_url: str, method: str, params: dict | None = None, *, retry: bool = True) -> dict:
    """Execute a CDP command via WebSocket.
    
    Args:
        ws_url: WebSocket URL for the page
        method: CDP method name (e.g., "Network.getCookies")
        params: Optional parameters for the command
    
    Returns:
        The result of the CDP command
    """
    global _cached_ws, _cached_ws_url

    if retry:
        # Retry once in case of stale cached connection
        try:
            return execute_cdp_command(ws_url, method, params, retry=False)
        except Exception:
            # Try again without the cached connection
            _cached_ws = _cached_ws_url = None

    if ws_url != _cached_ws_url or not _cached_ws:
        if _cached_ws:
            _cached_ws.close()
            _cached_ws = None

        # suppress_origin=True is required for some managed Chrome/CDP endpoints
        # (e.g. OpenClaw browser profile) that reject default Origin headers.
        try:
            ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
        except TypeError:
            # Older websocket-client versions may not support suppress_origin.
            ws = websocket.create_connection(ws_url, timeout=30)
        _cached_ws = ws
        _cached_ws_url = ws_url
    else:
        ws = _cached_ws

    command = {
        "id": 1,
        "method": method,
        "params": params or {}
    }
    ws.send(json.dumps(command))

    # Wait for response with matching ID
    while True:
        response = json.loads(ws.recv())
        if response.get("id") == 1:
            return response.get("result", {})


def get_page_cookies(ws_url: str) -> list[dict]:
    """Get all cookies for the page via CDP.
    
    This is the key function that avoids keychain access!
    Uses Network.getAllCookies CDP command to get cookies for all domains.
    
    Returns:
        List of cookie objects (dicts) including name, value, domain, path, etc.
    """
    result = execute_cdp_command(ws_url, "Network.getAllCookies")
    return result.get("cookies", [])


def get_page_html(ws_url: str) -> str:
    """Get the page HTML to extract CSRF token."""
    execute_cdp_command(ws_url, "Runtime.enable")
    result = execute_cdp_command(
        ws_url,
        "Runtime.evaluate",
        {"expression": "document.documentElement.outerHTML"}
    )
    return result.get("result", {}).get("value", "")


def get_document_root(ws_url: str) -> dict:
    """Get the document root node."""
    return execute_cdp_command(ws_url, "DOM.getDocument")["root"]


def query_selector(ws_url: str, node_id: int, selector: str) -> int | None:
    """Find a node ID using a CSS selector."""
    result = execute_cdp_command(
        ws_url, 
        "DOM.querySelector",
        {"nodeId": node_id, "selector": selector}
    )
    return result.get("nodeId") if result.get("nodeId") != 0 else None



def get_current_url(ws_url: str) -> str:
    """Get the current page URL."""
    execute_cdp_command(ws_url, "Runtime.enable")
    result = execute_cdp_command(
        ws_url,
        "Runtime.evaluate",
        {"expression": "window.location.href"}
    )
    return result.get("result", {}).get("value", "")


def navigate_to_url(ws_url: str, url: str) -> None:
    """Navigate the page to a URL."""
    execute_cdp_command(ws_url, "Page.enable")
    execute_cdp_command(ws_url, "Page.navigate", {"url": url})


def is_logged_in(url: str) -> bool:
    """Check login status by URL.
    
    If NotebookLM redirects to accounts.google.com, user is not logged in.
    """
    if "accounts.google.com" in url:
        return False
    if "notebooklm.google.com" in url:
        return True
    return False


def extract_build_label(html: str) -> str:
    """Extract the build label (bl) from page HTML.

    Google embeds the current build label under the 'cfb2h' key in the page's
    inline configuration JSON. This value is used as the 'bl' URL parameter
    in batchexecute and query requests.
    """
    match = re.search(r'"cfb2h":"([^"]+)"', html)
    return match.group(1) if match else ""


def extract_csrf_token(html: str) -> str:
    """Extract CSRF token from page HTML."""
    match = re.search(r'"SNlM0e":"([^"]+)"', html)
    return match.group(1) if match else ""


def extract_session_id(html: str) -> str:
    """Extract session ID from page HTML."""
    patterns = [
        r'"FdrFJe":"(\d+)"',
        r'f\.sid["\s:=]+["\']?(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return ""


def extract_email(html: str) -> str:
    """Extract user email from page HTML."""
    # Try various patterns Google uses to embed the email
    patterns = [
        r'"oPEP7c":"([^"]+@[^"]+)"',  # Google's internal email field
        r'data-email="([^"]+)"',  # data-email attribute
        r'"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"',  # Generic email in quotes
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html)
        for match in matches:
            # Filter out common false positives
            if '@google.com' not in match and '@gstatic' not in match:
                if '@' in match and '.' in match.split('@')[-1]:
                    return match
    return ""


def extract_cookies_via_cdp(
    port: int = CDP_DEFAULT_PORT,
    auto_launch: bool = True,
    wait_for_login: bool = True,
    login_timeout: int = 300,
    profile_name: str = "default",
    clear_profile: bool = False,
) -> dict[str, Any]:
    """Extract cookies and tokens from Chrome via CDP.
    
    This is the main entry point for CDP-based authentication.
    
    Args:
        port: Chrome DevTools port
        auto_launch: If True, launch Chrome if not running
        wait_for_login: If True, wait for user to log in
        login_timeout: Max seconds to wait for login
        profile_name: NLM profile name (each gets its own Chrome user-data-dir)
        clear_profile: If True, delete the Chrome user-data-dir before launching
    
    Returns:
        Dict with cookies, csrf_token, session_id, and email
    
    Raises:
        AuthenticationError: If extraction fails
    """
    if clear_profile:
        from notebooklm_tools.utils.config import get_chrome_profile_dir
        import shutil
        profile_dir = get_chrome_profile_dir(profile_name)
        if profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)
            
    # Check if Chrome is running with debugging
    # First, try to find an existing instance on any port in our range
    reused_existing = False
    existing_port, debugger_url = None, None
    if not clear_profile:
        existing_port, debugger_url = find_existing_nlm_chrome()
        
    if existing_port:
        port = existing_port
        reused_existing = True
    
    if not debugger_url and auto_launch:
        if is_profile_locked(profile_name):
            # Profile locked but no Chrome found on known ports - stale lock?
            raise AuthenticationError(
                message="The NLM auth profile is locked but no Chrome instance found",
                hint=f"Close any stuck Chrome processes or delete the SingletonLock file in the {profile_name} Chrome profile.",
            )
        
        if not get_chrome_path():
            raise AuthenticationError(
                message="Chrome not found",
                hint="Install Google Chrome or use 'nlm login --manual' to import cookies from a file.",
            )
        
        # Find an available port
        try:
            port = find_available_port()
        except RuntimeError as e:
            raise AuthenticationError(
                message=str(e),
                hint="Close some Chrome instances and try again.",
            )
        
        if not launch_chrome(port, profile_name=profile_name):
            raise AuthenticationError(
                message="Failed to launch Chrome",
                hint="Try 'nlm login --manual' to import cookies from a file.",
            )
        
        debugger_url = get_debugger_url(port, tries=5)
    
    if not debugger_url:
        raise AuthenticationError(
            message=f"Cannot connect to Chrome on port {port}",
            hint="Use 'nlm login --manual' to import cookies from a file.",
        )
    result = extract_cookies_from_page(f"http://localhost:{port}", wait_for_login, login_timeout)
    result["reused_existing"] = reused_existing
    return result

def extract_cookies_via_existing_cdp(
    cdp_url: str,
    wait_for_login: bool = True,
    login_timeout: int = 300,
) -> dict[str, Any]:
    """Extract auth cookies from an already-running Chrome CDP endpoint.

    This is used for provider-style auth integrations (e.g. OpenClaw-managed
    browser profiles) where Chrome lifecycle is managed externally.
    """
    try:
        cdp_http_url = normalize_cdp_http_url(cdp_url)
    except ValueError as e:
        raise AuthenticationError(message=str(e)) from e

    try:
        version = httpx_client.get(f"{cdp_http_url}/json/version", timeout=8)
        version.raise_for_status()
    except Exception as e:
        raise AuthenticationError(
            message=f"Cannot connect to CDP endpoint: {cdp_http_url}",
            hint="Ensure the browser is running and CDP is reachable.",
        ) from e
    return extract_cookies_from_page(cdp_http_url, wait_for_login, login_timeout)

def extract_cookies_from_page(
    cdp_http_url: str,
    wait_for_login: bool = True,
    login_timeout: int = 300,
) -> dict[str, Any]:

    page = find_or_create_notebooklm_page_by_cdp_url(cdp_http_url)
    if not page:
        raise AuthenticationError(
            message="Failed to open NotebookLM page",
            hint="Try manually navigating to notebooklm.google.com and try again.",
        )

    ws_url = page.get("webSocketDebuggerUrl")
    if not ws_url:
        raise AuthenticationError(
            message="No WebSocket URL for NotebookLM page",
            hint="The target browser may need a restart.",
        )

    # Navigate to NotebookLM if needed
    current_url = page.get("url", "")
    if "notebooklm.google.com" not in current_url:
        navigate_to_url(ws_url, NOTEBOOKLM_URL)

    # Check login status
    current_url = get_current_url(ws_url)

    if not is_logged_in(current_url) and wait_for_login:
        start_time = time.time()
        while time.time() - start_time < login_timeout:
            time.sleep(.5)
            try:
                current_url = get_current_url(ws_url)
                if is_logged_in(current_url):
                    break
            except Exception:
                pass

        if not is_logged_in(current_url):
            raise AuthenticationError(
                message="Login timeout",
                hint="Please log in to NotebookLM in the connected browser window.",
            )

    # Extract cookies
    cookies = get_page_cookies(ws_url)

    if not cookies:
        raise AuthenticationError(
            message="No cookies extracted",
            hint="Make sure you're fully logged in.",
        )

    # Get page HTML for CSRF, session ID, email, and build label
    html = get_page_html(ws_url)
    csrf_token = extract_csrf_token(html)
    session_id = extract_session_id(html)
    email = extract_email(html)
    build_label = extract_build_label(html)

    return {
        "cookies": cookies,
        "csrf_token": csrf_token,
        "session_id": session_id,
        "email": email,
        "build_label": build_label,
    }


# =============================================================================
# Headless Authentication (for automatic token refresh)
# =============================================================================

def has_chrome_profile(profile_name: str = "default") -> bool:
    """Check if a Chrome profile with saved login exists.
    
    Returns True if the profile directory exists and has login cookies,
    indicating that the user has previously authenticated.
    """
    profile_dir = get_chrome_profile_dir(profile_name)
    # Check for Cookies file which indicates the profile has been used
    cookies_file = profile_dir / "Default" / "Cookies"
    return cookies_file.exists()


def cleanup_chrome_profile_cache(profile_name: str = "default") -> int:
    """Remove unnecessary cache directories to minimize profile size.
    
    Keeps cookies and login data intact while removing caches that can
    grow to hundreds of MB. Safe to run after successful authentication.
    
    Args:
        profile_name: The profile name to clean up.
        
    Returns:
        Number of bytes freed.
    """
    profile_dir = get_chrome_profile_dir(profile_name)
    
    # Cache directories that are safe to remove (not needed for auth)
    cache_dirs = [
        "Cache",
        "Code Cache", 
        "Service Worker",
        "GPUCache",
        "DawnWebGPUCache",
        "DawnGraphiteCache",
        "ShaderCache",
        "GrShaderCache",
    ]
    
    bytes_freed = 0
    default_dir = profile_dir / "Default"
    
    for cache_dir in cache_dirs:
        cache_path = default_dir / cache_dir
        if cache_path.exists():
            try:
                # Calculate size before deletion
                size = sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file())
                shutil.rmtree(cache_path, ignore_errors=True)
                bytes_freed += size
            except Exception:
                pass
    
    return bytes_freed


def run_headless_auth(
    port: int = 9223,
    timeout: int = 30,
    profile_name: str = "default",
) -> "AuthTokens | None":
    """Run authentication in headless mode (no user interaction).
    
    This only works if the Chrome profile already has saved Google login.
    The Chrome process is automatically terminated after token extraction.
    
    Used for automatic token refresh when cached tokens expire.
    
    Args:
        port: Chrome DevTools port (use different port to avoid conflicts)
        timeout: Maximum time to wait for auth extraction
        profile_name: The profile name to use for Chrome
        
    Returns:
        AuthTokens if successful, None if failed or no saved login
    """
    # Import here to avoid circular imports
    from notebooklm_tools.core.auth import AuthTokens, save_tokens_to_cache, validate_cookies
    
    # Check if profile exists with saved login
    if not has_chrome_profile(profile_name):
        return None

    chrome_process: subprocess.Popen | None = None
    chrome_was_running = False

    try:
        # Try to connect to existing Chrome first
        debugger_url = get_debugger_url(port)

        if debugger_url:
            # Chrome already running - use existing instance
            chrome_was_running = True
        else:
            # No Chrome running - launch in headless mode
            chrome_process = launch_chrome_process(port, headless=True, profile_name=profile_name)
            if not chrome_process:
                return None

            # Wait for Chrome debugger to be ready
            debugger_url = get_debugger_url(port, tries=5)
            if not debugger_url:
                return None
        
        # Find or create NotebookLM page
        page = find_or_create_notebooklm_page(port)
        if not page:
            return None
        
        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            return None
        
        # Check if logged in by URL
        current_url = get_current_url(ws_url)
        if not is_logged_in(current_url):
            # Not logged in - headless can't help
            return None
        
        # Extract cookies
        cookies_list = get_page_cookies(ws_url)
        cookies = {c["name"]: c["value"] for c in cookies_list}
        
        if not validate_cookies(cookies):
            return None
        
        # Get page HTML for CSRF extraction
        html = get_page_html(ws_url)
        csrf_token = extract_csrf_token(html)
        session_id = extract_session_id(html)
        
        # Create and save tokens
        tokens = AuthTokens(
            cookies=cookies,
            csrf_token=csrf_token or "",
            session_id=session_id or "",
            extracted_at=time.time(),
        )
        save_tokens_to_cache(tokens)
        
        # Clean up cache to minimize profile size
        cleanup_chrome_profile_cache(profile_name)
        
        return tokens
        
    except Exception:
        return None
        
    finally:
        # IMPORTANT: Only terminate Chrome if we launched it
        # Don't terminate if we connected to existing Chrome instance
        if chrome_process and not chrome_was_running:
            terminate_chrome(chrome_process, port)
