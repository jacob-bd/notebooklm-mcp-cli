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

import httpx

from notebooklm_tools.core.exceptions import AuthenticationError


CDP_DEFAULT_PORT = 9222
CDP_PORT_RANGE = range(9222, 9232)  # Ports to scan for existing/available
NOTEBOOKLM_URL = "https://notebooklm.google.com/"


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
                s.bind(('localhost', port))
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


def find_existing_nlm_chrome(port_range: range = CDP_PORT_RANGE) -> int | None:
    """Find an existing NLM Chrome instance on any port in range.
    
    Scans the port range looking for a Chrome DevTools endpoint.
    This allows reconnecting to an existing auth Chrome window.
    
    Returns:
        The port number if found, None otherwise
    """
    for port in port_range:
        try:
            response = httpx.get(f"http://localhost:{port}/json/version", timeout=2)
            if response.status_code == 200:
                # Found a Chrome DevTools endpoint
                return port
        except Exception:
            continue
    return None


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
        # Wait for Chrome to start
        time.sleep(3)
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


def terminate_chrome() -> bool:
    """Terminate the Chrome process launched by this module.
    
    This releases the profile lock so headless auth can work later.
    
    Returns:
        True if Chrome was terminated, False if no process to terminate.
    """
    global _chrome_process
    if _chrome_process is None:
        return False
    
    try:
        _chrome_process.terminate()
        _chrome_process.wait(timeout=5)
    except Exception:
        try:
            _chrome_process.kill()
        except Exception:
            pass
    
    _chrome_process = None
    return True


def get_debugger_url(port: int = CDP_DEFAULT_PORT) -> str | None:
    """Get the WebSocket debugger URL for Chrome."""
    try:
        response = httpx.get(f"http://localhost:{port}/json/version", timeout=5)
        data = response.json()
        return data.get("webSocketDebuggerUrl")
    except Exception:
        return None


def get_pages(port: int = CDP_DEFAULT_PORT) -> list[dict]:
    """Get list of open pages in Chrome."""
    try:
        response = httpx.get(f"http://localhost:{port}/json", timeout=5)
        return response.json()
    except Exception:
        return []


def find_or_create_notebooklm_page(port: int = CDP_DEFAULT_PORT) -> dict | None:
    """Find an existing NotebookLM page or create a new one."""
    from urllib.parse import quote
    
    pages = get_pages(port)
    
    # Look for existing NotebookLM page
    for page in pages:
        url = page.get("url", "")
        if "notebooklm.google.com" in url:
            return page
    
    # Create a new page
    try:
        encoded_url = quote(NOTEBOOKLM_URL, safe="")
        response = httpx.put(
            f"http://localhost:{port}/json/new?{encoded_url}",
            timeout=15
        )
        if response.status_code == 200 and response.text.strip():
            return response.json()
        
        # Fallback: create blank page then navigate
        response = httpx.put(f"http://localhost:{port}/json/new", timeout=10)
        if response.status_code == 200 and response.text.strip():
            page = response.json()
            ws_url = page.get("webSocketDebuggerUrl")
            if ws_url:
                navigate_to_url(ws_url, NOTEBOOKLM_URL)
            return page
        
        return None
    except Exception:
        return None


def execute_cdp_command(ws_url: str, method: str, params: dict | None = None) -> dict:
    """Execute a CDP command via WebSocket.
    
    Args:
        ws_url: WebSocket URL for the page
        method: CDP method name (e.g., "Network.getCookies")
        params: Optional parameters for the command
    
    Returns:
        The result of the CDP command
    """
    try:
        import websocket
    except ImportError:
        raise AuthenticationError(
            message="websocket-client package not installed",
            hint="Run 'pip install websocket-client' to install it.",
        )
    
    ws = websocket.create_connection(ws_url, timeout=30)
    try:
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
    finally:
        ws.close()


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
    time.sleep(3)  # Wait for page to load


def is_logged_in(url: str) -> bool:
    """Check login status by URL.
    
    If NotebookLM redirects to accounts.google.com, user is not logged in.
    """
    if "accounts.google.com" in url:
        return False
    if "notebooklm.google.com" in url:
        return True
    return False


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
        r'"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"',  # Generic email in quotes
        r'data-email="([^"]+)"',  # data-email attribute
        r'"oPEP7c":"([^"]+@[^"]+)"',  # Google's internal email field
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
) -> dict[str, Any]:
    """Extract cookies and tokens from Chrome via CDP.
    
    This is the main entry point for CDP-based authentication.
    
    Args:
        port: Chrome DevTools port
        auto_launch: If True, launch Chrome if not running
        wait_for_login: If True, wait for user to log in
        login_timeout: Max seconds to wait for login
        profile_name: NLM profile name (each gets its own Chrome user-data-dir)
    
    Returns:
        Dict with cookies, csrf_token, session_id, and email
    
    Raises:
        AuthenticationError: If extraction fails
    """
    # Check if Chrome is running with debugging
    # First, try to find an existing instance on any port in our range
    existing_port = find_existing_nlm_chrome()
    if existing_port:
        port = existing_port
        debugger_url = get_debugger_url(port)
    else:
        debugger_url = None
    
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
        
        debugger_url = get_debugger_url(port)
    
    if not debugger_url:
        raise AuthenticationError(
            message=f"Cannot connect to Chrome on port {port}",
            hint="Use 'nlm login --manual' to import cookies from a file.",
        )
    
    # Find or create NotebookLM page
    page = find_or_create_notebooklm_page(port)
    if not page:
        raise AuthenticationError(
            message="Failed to open NotebookLM page",
            hint="Try manually navigating to notebooklm.google.com in Chrome.",
        )
    
    ws_url = page.get("webSocketDebuggerUrl")
    if not ws_url:
        raise AuthenticationError(
            message="No WebSocket URL for page",
            hint="Chrome may need to be restarted.",
        )
    
    # Navigate to NotebookLM if needed
    current_url = page.get("url", "")
    if "notebooklm.google.com" not in current_url:
        navigate_to_url(ws_url, NOTEBOOKLM_URL)
    
    # Check login status
    current_url = get_current_url(ws_url)
    
    if not is_logged_in(current_url) and wait_for_login:
        # Wait for login
        start_time = time.time()
        while time.time() - start_time < login_timeout:
            time.sleep(5)
            try:
                current_url = get_current_url(ws_url)
                if is_logged_in(current_url):
                    break
            except Exception:
                pass
        
        if not is_logged_in(current_url):
            raise AuthenticationError(
                message="Login timeout",
                hint="Please log in to NotebookLM in the Chrome window.",
            )
    
    # Extract cookies
    cookies = get_page_cookies(ws_url)
    
    if not cookies:
        raise AuthenticationError(
            message="No cookies extracted",
            hint="Make sure you're fully logged in.",
        )
    
    # Get page HTML for CSRF, session ID, and email
    html = get_page_html(ws_url)
    csrf_token = extract_csrf_token(html)
    session_id = extract_session_id(html)
    email = extract_email(html)
    
    return {
        "cookies": cookies,
        "csrf_token": csrf_token,
        "session_id": session_id,
        "email": email,
    }
