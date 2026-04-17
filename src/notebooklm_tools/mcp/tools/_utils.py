"""MCP Tools - Shared utilities and base components."""

import functools
import inspect
import json
import logging
import os
import threading
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeAlias, TypeVar, cast

from notebooklm_tools.core.auth import load_cached_tokens
from notebooklm_tools.core.client import NotebookLMClient
from notebooklm_tools.core.utils import extract_cookies_from_chrome_export

# MCP request/response logger
mcp_logger = logging.getLogger("notebooklm_tools.mcp")

# Parameters that must never appear in log output
_SENSITIVE_PARAMS = frozenset({"cookies", "csrf_token", "session_id", "request_body"})
P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")
ResultDict: TypeAlias = dict[str, Any]
_StrConverter: TypeAlias = Callable[[Any], str]
_DEFAULT_STR_CONVERTER: _StrConverter = str


def _sanitize_params(params: ResultDict) -> ResultDict:
    """Replace sensitive parameter values with [REDACTED] before logging."""
    return {k: "[REDACTED]" if k in _SENSITIVE_PARAMS else v for k, v in params.items()}


def error_result(
    error: str,
    *,
    hint: str | None = None,
    status: str = "error",
    **extra: Any,
) -> ResultDict:
    """Build a consistent error payload for MCP tools."""
    result: ResultDict = {"status": status, "error": error}
    if hint:
        result["hint"] = hint
    result.update(extra)
    return result


# Global state
_client: NotebookLMClient | None = None
_client_lock = threading.Lock()
_query_timeout: float = float(os.environ.get("NOTEBOOKLM_QUERY_TIMEOUT", "120.0"))


def get_query_timeout() -> float:
    """Get the query timeout value."""
    return _query_timeout


def set_query_timeout(timeout: float) -> None:
    """Set the query timeout value."""
    global _query_timeout
    _query_timeout = timeout


def get_client() -> NotebookLMClient:
    """Get or create the API client (thread-safe).

    Tries environment variables first, falls back to cached tokens from auth CLI.
    """
    global _client

    with _client_lock:
        # Profile-change detection (only when env-var auth is not in use).
        # Runs inside the lock so that _client reads and writes are always
        # serialised — fixing the double-checked locking race condition (M-2).
        cookie_header = os.environ.get("NOTEBOOKLM_COOKIES", "")
        if not cookie_header and _client is not None:
            try:
                from notebooklm_tools.utils.config import reset_config

                # Reset config so we read the latest default_profile from disk
                # in case `nlm login switch` was run in another terminal
                reset_config()
                cached = load_cached_tokens()

                # Force re-init if cookies changed (profile switch) OR if disk
                # tokens are newer than the running client (same-profile re-auth
                # via `nlm login` — fixes Issue #161).
                if cached:
                    cookies_changed = getattr(_client, "cookies", None) != cached.cookies
                    disk_is_newer = cached.extracted_at > getattr(_client, "_created_at", 0)
                    if cookies_changed or disk_is_newer:
                        mcp_logger.info("Authentication change detected, reloading client.")
                        _client = None  # Reset directly; lock already held
            except Exception as e:
                mcp_logger.debug(f"Failed to check auth status: {e}")

        if _client is not None:
            return _client

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
    with _client_lock:
        _client = None


def get_mcp_instance() -> Any:
    """Get the FastMCP instance. Import here to avoid circular imports."""
    from notebooklm_tools.mcp.server import mcp

    return mcp


# Registry for tools - allows registration without immediate mcp dependency
_tool_registry: list[tuple[str, Callable[..., Any]]] = []


def logged_tool() -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator that adds MCP request/response logging to a tool.

    Decorated tools are added to the internal registry for later MCP server
    registration via ``register_all_tools()`` rather than being registered
    immediately when decorated. Supports both synchronous and asynchronous
    functions.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            async_func = cast(Callable[P, Awaitable[Any]], func)

            @functools.wraps(async_func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                tool_name = async_func.__name__
                if mcp_logger.isEnabledFor(logging.DEBUG):
                    params = _sanitize_params({k: v for k, v in kwargs.items() if v is not None})
                    mcp_logger.debug(f"MCP Request: {tool_name}({json.dumps(params, default=str)})")

                result: Any = await async_func(*args, **kwargs)

                if mcp_logger.isEnabledFor(logging.DEBUG):
                    result_str = json.dumps(result, default=str)
                    if len(result_str) > 1000:
                        result_str = result_str[:1000] + "..."
                    mcp_logger.debug(f"MCP Response: {tool_name} -> {result_str}")

                return result

            wrapper = cast(Callable[P, R], async_wrapper)
        else:
            sync_func = func

            @functools.wraps(sync_func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                tool_name = sync_func.__name__
                if mcp_logger.isEnabledFor(logging.DEBUG):
                    params = _sanitize_params({k: v for k, v in kwargs.items() if v is not None})
                    mcp_logger.debug(f"MCP Request: {tool_name}({json.dumps(params, default=str)})")

                result: R = sync_func(*args, **kwargs)

                if mcp_logger.isEnabledFor(logging.DEBUG):
                    result_str = json.dumps(result, default=str)
                    if len(result_str) > 1000:
                        result_str = result_str[:1000] + "..."
                    mcp_logger.debug(f"MCP Response: {tool_name} -> {result_str}")

                return result

            wrapper = sync_wrapper

        # Store for later registration
        _tool_registry.append((func.__name__, cast(Callable[..., Any], wrapper)))
        return wrapper

    return decorator


def register_all_tools(mcp: Any) -> None:
    """Register all collected tools with the MCP instance."""
    for _, wrapper in _tool_registry:
        mcp.tool()(wrapper)


# Essential cookies for NotebookLM API authentication
ESSENTIAL_COOKIES = [
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",  # Core auth cookies
    "__Secure-1PSID",
    "__Secure-3PSID",  # Secure session variants
    "__Secure-1PAPISID",
    "__Secure-3PAPISID",  # Secure API variants
    "OSID",
    "__Secure-OSID",  # Origin-bound session
    "__Secure-1PSIDTS",
    "__Secure-3PSIDTS",  # Timestamp tokens (rotate frequently)
    "SIDCC",
    "__Secure-1PSIDCC",
    "__Secure-3PSIDCC",  # Session cookies (rotate frequently)
]


def coerce_list(
    val: object | None,
    item_type: Callable[[Any], T] = _DEFAULT_STR_CONVERTER,
) -> list[T] | None:
    """Coerce a value into a list of ``item_type``.

    MCP clients (Claude Desktop, Cursor, etc.) may serialize list parameters as:
      - An actual Python list  → pass through
      - A JSON string          → ``'["a","b"]'``
      - A comma-separated str  → ``'a,b,c'``
      - A single bare value    → ``'a'``
      - None                   → ``None``

    This helper normalizes all forms into ``list[item_type]`` while preserving
    ``None`` as ``None`` for "use default / all" semantics.
    """
    converter = item_type
    if val is None:
        return None  # Preserve None semantics (means "use default / all")
    if isinstance(val, list):
        return [converter(x) for x in val]
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        if val.startswith("["):
            try:
                return [converter(x) for x in json.loads(val)]
            except (json.JSONDecodeError, ValueError):
                pass  # Fall through to comma-split
        return [converter(x.strip()) for x in val.split(",") if x.strip()]
    # Single non-string value (e.g. an int)
    return [converter(val)]
