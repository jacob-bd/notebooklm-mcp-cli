"""Rate limiting for NotebookLM API requests.

Implements a simple token bucket algorithm to prevent API abuse and
ensure respectful use of Google's services.
"""

import threading
import time
from typing import NamedTuple


class RateLimitConfig(NamedTuple):
    """Configuration for rate limiting."""

    requests_per_second: float = 10.0  # Max sustained rate
    burst_size: int = 20  # Max burst requests


class TokenBucket:
    """Token bucket rate limiter with thread safety.

    Allows up to `burst_size` requests immediately, then refills at
    `requests_per_second` rate. Provides smooth rate limiting that
    permits bursts while enforcing long-term limits.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize the token bucket.

        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()
        self.capacity = self.config.burst_size
        self.tokens = float(self.capacity)
        self.fill_rate = self.config.requests_per_second
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time (called under lock)."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        self.last_update = now

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: float | None = None) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default 1)
            blocking: If True, wait for tokens to become available
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            True if tokens were acquired, False if timed out (non-blocking only)

        Raises:
            ValueError: If tokens > capacity
        """
        if tokens > self.capacity:
            raise ValueError(f"Cannot acquire {tokens} tokens (capacity: {self.capacity})")

        deadline = None if timeout is None else time.monotonic() + timeout

        while True:
            with self._lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                if not blocking:
                    return False

                # Calculate sleep time until tokens available
                tokens_needed = tokens - self.tokens
                sleep_time = tokens_needed / self.fill_rate

                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    sleep_time = min(sleep_time, remaining)

            # Sleep outside the lock
            time.sleep(min(sleep_time, 0.1))  # Wake up periodically to recheck

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        return self.acquire(tokens, blocking=False)

    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_update = time.monotonic()


# Global rate limiter instance (can be overridden for testing)
_global_limiter: TokenBucket | None = None


def get_rate_limiter() -> TokenBucket:
    """Get the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = TokenBucket()
    return _global_limiter


def set_rate_limiter(limiter: TokenBucket | None) -> None:
    """Set a custom global rate limiter (useful for testing)."""
    global _global_limiter
    _global_limiter = limiter


def rate_limit(tokens: int = 1, timeout: float | None = None) -> None:
    """Apply rate limiting before making an API call.

    Args:
        tokens: Number of tokens to acquire (default 1)
        timeout: Max seconds to wait for tokens

    Raises:
        TimeoutError: If tokens cannot be acquired within timeout
    """
    limiter = get_rate_limiter()
    if not limiter.acquire(tokens, timeout=timeout):
        raise TimeoutError(f"Rate limit: could not acquire {tokens} tokens within {timeout}s")
