"""Retry logic for transient server errors.

Provides exponential backoff retry for 5xx and 429 errors from Google's APIs.
Used by _call_rpc() and file upload methods.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

import httpx

logger = logging.getLogger("notebooklm_mcp.api")

# Status codes that warrant a retry (transient errors)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 16.0  # seconds


def is_retryable_error(exc: Exception) -> bool:
    """Check if an exception is a retryable server error."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return False


def retry_on_server_error(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
) -> Callable:
    """Decorator that retries a function on transient server errors.

    Uses exponential backoff: delay = min(base_delay * 2^attempt, max_delay)

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay between retries.

    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if not is_retryable_error(e) or attempt == max_retries:
                        raise
                    last_exception = e
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    status = e.response.status_code
                    logger.warning(
                        f"Server error {status} on attempt {attempt + 1}/{max_retries + 1}, "
                        f"retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            # Should not reach here, but just in case
            raise last_exception  # type: ignore[misc]
        return wrapper
    return decorator


def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    **kwargs: Any,
) -> Any:
    """Execute a callable with retry logic for transient server errors.

    Use this for one-off retry wrapping where a decorator isn't practical
    (e.g., inline httpx calls in upload methods).

    Args:
        func: The callable to execute.
        *args: Positional arguments for the callable.
        max_retries: Maximum retry attempts.
        base_delay: Initial backoff delay in seconds.
        max_delay: Maximum backoff delay in seconds.
        **kwargs: Keyword arguments for the callable.

    Returns:
        The return value of the callable.

    Raises:
        httpx.HTTPStatusError: If all retries are exhausted or error is non-retryable.
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if not is_retryable_error(e) or attempt == max_retries:
                raise
            last_exception = e
            delay = min(base_delay * (2 ** attempt), max_delay)
            status = e.response.status_code
            logger.warning(
                f"Server error {status} on attempt {attempt + 1}/{max_retries + 1}, "
                f"retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
    raise last_exception  # type: ignore[misc]
