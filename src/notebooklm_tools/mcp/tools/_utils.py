"""MCP Tools - Shared utilities and base components."""

import functools
import json
import logging
import os
from typing import Any

from notebooklm_tools.core.client import NotebookLMClient, extract_cookies_from_chrome_export
from notebooklm_tools.core.auth import load_cached_tokens

# MCP request/response logger
mcp_logger = logging.getLogger("notebooklm_tools.mcp")

# Global state
_client: NotebookLMClient | None = None
_query_timeout: float = float(os.environ.get("NOTEBOOKLM_QUERY_TIMEOUT", "120.0"))


def get_query_timeout() -> float:
    """Get the query timeout value."""
    return _query_timeout


def set_query_timeout(timeout: float) -> None:
    """Set the query timeout value."""
    global _query_timeout
    _query_timeout = timeout


def get_client() -> NotebookLMClient:
    """Get or create the API client.

    Tries environment variables first, falls back to cached tokens from auth CLI.
    """
    global _client
    if _client is None:
        cookie_header = os.environ.get("NOTEBOOKLM_COOKIES", "")
        csrf_token = os.environ.get("NOTEBOOKLM_CSRF_TOKEN", "")
        session_id = os.environ.get("NOTEBOOKLM_SESSION_ID", "")

        build_label = ""

        if cookie_header:
            # Use environment variables
            cookies = extract_cookies_from_chrome_export(cookie_header)
        else:
            # Try cached tokens from auth CLI
            cached = load_cached_tokens()
            if cached:
                cookies = cached.cookies
                csrf_token = csrf_token or cached.csrf_token
                session_id = session_id or cached.session_id
                build_label = cached.build_label or ""
            else:
                raise ValueError(
                    "No authentication found. Either:\n"
                    "1. Run 'nlm login' to authenticate via Chrome, or\n"
                    "2. Set NOTEBOOKLM_COOKIES environment variable manually"
                )

        _client = NotebookLMClient(
            cookies=cookies,
            csrf_token=csrf_token,
            session_id=session_id,
            build_label=build_label,
        )
    return _client


def reset_client() -> None:
    """Reset the client to force re-initialization."""
    global _client
    _client = None


def get_mcp_instance():
    """Get the FastMCP instance. Import here to avoid circular imports."""
    from notebooklm_tools.mcp.server import mcp
    return mcp


# Registry for tools - allows registration without immediate mcp dependency
_tool_registry: list[tuple] = []


import inspect

def logged_tool():
    """Decorator that combines @mcp.tool() with MCP request/response logging.
    
    Tools are registered immediately with the MCP server when decorated.
    Supports both synchronous and asynchronous functions.
    """
    def decorator(func):
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tool_name = func.__name__
                if mcp_logger.isEnabledFor(logging.DEBUG):
                    params = {k: v for k, v in kwargs.items() if v is not None}
                    mcp_logger.debug(f"MCP Request: {tool_name}({json.dumps(params, default=str)})")
                
                result = await func(*args, **kwargs)
                
                if mcp_logger.isEnabledFor(logging.DEBUG):
                    result_str = json.dumps(result, default=str)
                    if len(result_str) > 1000:
                        result_str = result_str[:1000] + "..."
                    mcp_logger.debug(f"MCP Response: {tool_name} -> {result_str}")
                
                return result
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                tool_name = func.__name__
                if mcp_logger.isEnabledFor(logging.DEBUG):
                    params = {k: v for k, v in kwargs.items() if v is not None}
                    mcp_logger.debug(f"MCP Request: {tool_name}({json.dumps(params, default=str)})")
                
                result = func(*args, **kwargs)
                
                if mcp_logger.isEnabledFor(logging.DEBUG):
                    result_str = json.dumps(result, default=str)
                    if len(result_str) > 1000:
                        result_str = result_str[:1000] + "..."
                    mcp_logger.debug(f"MCP Response: {tool_name} -> {result_str}")
                
                return result
        
        # Store for later registration
        _tool_registry.append((func.__name__, wrapper))
        return wrapper
    return decorator


def register_all_tools(mcp):
    """Register all collected tools with the MCP instance."""
    for name, wrapper in _tool_registry:
        mcp.tool()(wrapper)


# Essential cookies for NotebookLM API authentication
ESSENTIAL_COOKIES = [
    "SID", "HSID", "SSID", "APISID", "SAPISID",  # Core auth cookies
    "__Secure-1PSID", "__Secure-3PSID",  # Secure session variants
    "__Secure-1PAPISID", "__Secure-3PAPISID",  # Secure API variants
    "OSID", "__Secure-OSID",  # Origin-bound session
    "__Secure-1PSIDTS", "__Secure-3PSIDTS",  # Timestamp tokens (rotate frequently)
    "SIDCC", "__Secure-1PSIDCC", "__Secure-3PSIDCC",  # Session cookies (rotate frequently)
]
