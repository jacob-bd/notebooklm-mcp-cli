"""Service layer for auth.

Thin re-export of auth-related symbols from `core.auth` so the MCP/CLI
layers can satisfy the layering rule (`cli/` and `mcp/` must not import
from `core/`). Business logic, validation, and error handling for auth
live in `notebooklm_tools.core.auth`; this module is intentionally a
shim and adds no behavior of its own.

Three mechanisms are used to preserve test monkeypatching of the
underlying `core.auth` symbols:

1. **Function wrappers** (`check_auth`, `load_cached_tokens`,
   `save_tokens_to_cache`, `get_cache_path`, `validate_cookies`) resolve
   the implementation lazily on every call. This is the same pattern
   that would otherwise silently fail if the symbol were captured at
   import time.

2. **PEP 562 module-level `__getattr__`** for the two class symbols
   (`AuthTokens`, `AuthManager`). Each attribute access re-exports
   the class from `core.auth` lazily, so `from notebooklm_tools.
   services.auth import AuthManager` inside a test function (after a
   `monkeypatch.setattr` of `core.auth.AuthManager`) still picks up the
   patched class. Since we resolve the same `core.auth.X` each time,
   `isinstance(x, services.auth.AuthManager)` continues to return True
   for instances constructed via the shim.

3. **No re-export of internal helpers** (`AuthManager.list_profiles`,
   etc.) — the shim is intentionally a thin surface that the layering
   rule is allowed to grow into. Anything not listed in `__all__` or
   resolved via `__getattr__` is intentionally absent.
"""

from notebooklm_tools.core import auth as _core_auth

__all__ = [
    "AuthManager",  # noqa: F822 — provided lazily via PEP 562 __getattr__
    "AuthTokens",  # noqa: F822 — provided lazily via PEP 562 __getattr__
    "check_auth",
    "get_cache_path",
    "load_cached_tokens",
    "save_tokens_to_cache",
    "validate_cookies",
]


def check_auth(*args, **kwargs):
    """Re-export of `notebooklm_tools.core.auth.check_auth`.

    Resolves the implementation lazily on each call so that monkeypatching
    `notebooklm_tools.core.auth.check_auth` (a common test pattern) is
    observed by callers of this shim.
    """
    return _core_auth.check_auth(*args, **kwargs)


def load_cached_tokens():
    """Re-export of `notebooklm_tools.core.auth.load_cached_tokens`."""
    return _core_auth.load_cached_tokens()


def save_tokens_to_cache(tokens, silent: bool = False):
    """Re-export of `notebooklm_tools.core.auth.save_tokens_to_cache`."""
    return _core_auth.save_tokens_to_cache(tokens, silent=silent)


def get_cache_path():
    """Re-export of `notebooklm_tools.core.auth.get_cache_path`."""
    return _core_auth.get_cache_path()


def validate_cookies(cookies):
    """Re-export of `notebooklm_tools.core.auth.validate_cookies`."""
    return _core_auth.validate_cookies(cookies)


def get_active_auth_mtime() -> float:
    """Return the most recent mtime of any auth storage on disk, or 0.0.

    The CLI/MCP codebase stores auth in two layouts that can coexist:

    - **Modern (multi-profile):** `~/.notebooklm-mcp-cli/profiles/<name>/cookies.json`
      for each profile `<name>` in the profiles directory.
    - **Legacy (single-profile):** `~/.notebooklm-mcp-cli/auth.json` at the
      storage root, used by older installs and some MCP clients.

    The auth-guard mtime check needs to invalidate on a write to ANY of
    these files, not just the one for the "default" profile — because the
    active profile for a given MCP/CLI session can be overridden with
    `--profile`, while the config-level `default_profile` stays put. If
    we only watched the config-default profile's file, an external
    `nlm login --profile <other>` would silently fail to invalidate the
    guard (live-testing caught this exact bug in v0.6.15 prep).

    This function stats every `cookies.json` under `profiles/`, the
    legacy `auth.json` at the storage root, and returns the max mtime.
    A write to any of them invalidates the guard. Returns 0.0 if no auth
    file exists yet (sentinel for "no cache yet").

    Catches all exceptions and returns 0.0 on error: a wrong mtime answer
    is far less harmful than a 500 on `studio_create` from an unrelated
    config error.
    """
    try:
        import contextlib

        from notebooklm_tools.utils.config import get_profiles_dir, get_storage_dir

        candidates = [get_storage_dir() / "auth.json"]
        try:
            profiles_dir = get_profiles_dir()
            candidates.extend(profiles_dir.glob("*/cookies.json"))
        except (OSError, FileNotFoundError):
            pass

        latest = 0.0
        for path in candidates:
            with contextlib.suppress(OSError, FileNotFoundError):
                latest = max(latest, path.stat().st_mtime)
        return latest
    except Exception:
        return 0.0


_LAZY_CLASS_NAMES = frozenset({"AuthTokens", "AuthManager", "AuthHealthChecker"})


def __getattr__(name):
    """PEP 562 lazy re-export of class symbols from `core.auth`.

    Resolves to the current class object from `core.auth` on every
    attribute access. We intentionally do NOT cache the result in the
    module globals: a top-level import (e.g. `from notebooklm_tools.
    services.auth import AuthManager` in `cli/utils.py`) would poison
    the cache for any test that monkeypatches `core.auth.AuthManager`
    afterward, because subsequent attribute accesses within a function
    body would find the cached original instead of the patched class.

    The per-access cost is one extra Python attribute lookup — negligible
    against the HTTP roundtrip or filesystem work that surrounds every
    AuthManager/AuthTokens usage.
    """
    if name in _LAZY_CLASS_NAMES:
        from notebooklm_tools.core.auth import (
            AuthHealthChecker,
            AuthManager,
            AuthTokens,
        )

        return {
            "AuthTokens": AuthTokens,
            "AuthManager": AuthManager,
            "AuthHealthChecker": AuthHealthChecker,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
