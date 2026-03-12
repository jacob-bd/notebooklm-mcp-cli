"""SQLite-backed cache with TTL, compression, and connection pooling.

Architecture:
- Thread-local SQLite connections (one connection per thread, WAL mode for concurrent reads)
- zlib compression for values > 1KB (keeps DB small for large source content)
- Pluggable backend: ``CacheBackend`` ABC allows swapping SQLite for Redis/KV/D1
- Single write-lock for mutation operations

Storage: ~/.notebooklm-mcp-cli/cache.db

TTL values:
  notebook_list    300s  (5 min)   — changes on create/delete
  notebook         300s  (5 min)   — sources change on add/delete
  notebook_summary 86400s (24 hr)  — AI-generated, expensive
  source_guide     86400s (24 hr)  — AI-generated, expensive
  source_content   3600s  (1 hr)   — raw text, rarely changes
  source_freshness 600s   (10 min) — Drive stale check result
"""

import json
import logging
import sqlite3
import threading
import time
import zlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .config import get_storage_dir

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants
# ---------------------------------------------------------------------------

TTL: dict[str, int] = {
    "notebook_list":      300,
    "notebook":           300,
    "notebook_summary":   86400,
    "source_guide":       86400,
    "source_content":     3600,
    "source_freshness":   600,
}

# Compress serialized values larger than this (bytes)
_COMPRESS_THRESHOLD = 1024

# Thread-local storage: one SQLite connection per thread
_thread_local = threading.local()

# ---------------------------------------------------------------------------
# Abstract backend (pluggable: SQLite local, Redis, Cloudflare KV/D1, etc.)
# ---------------------------------------------------------------------------


class CacheBackend(ABC):
    """Abstract cache backend. Swap implementations without touching services."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return value or None on miss/expiry."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store value with TTL (seconds)."""

    @abstractmethod
    def invalidate(self, prefix: str) -> int:
        """Delete entries with this exact key or key prefix. Returns count."""

    @abstractmethod
    def list_entries(self) -> list[dict]:
        """Return all live entries: key, type, ttl_remaining_seconds, value_bytes."""

    @abstractmethod
    def clear_expired(self) -> int:
        """Delete expired entries. Returns count."""

    @abstractmethod
    def clear_all(self) -> int:
        """Delete all entries. Returns count."""


# ---------------------------------------------------------------------------
# SQLite backend (default)
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_entries (
    key        TEXT    PRIMARY KEY,
    value      BLOB    NOT NULL,
    compressed INTEGER NOT NULL DEFAULT 0,
    expires_at REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expires ON cache_entries(expires_at);
"""


class SQLiteCacheBackend(CacheBackend):
    """Thread-safe SQLite cache with WAL mode + per-thread connection pooling."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = str(db_path)
        self._write_lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------
    # Connection pool (thread-local)
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Return a cached per-thread connection, creating it if needed."""
        conn = getattr(_thread_local, f"nlm_conn_{id(self)}", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")    # concurrent readers
            conn.execute("PRAGMA synchronous=NORMAL")   # fast writes, crash-safe
            conn.execute("PRAGMA cache_size=-8000")     # 8MB page cache per thread
            setattr(_thread_local, f"nlm_conn_{id(self)}", conn)
        return conn

    def _init_db(self) -> None:
        with self._write_lock:
            conn = self._conn()
            conn.executescript(_SCHEMA)
            conn.commit()

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(value: Any) -> tuple[bytes, bool]:
        """JSON-serialize and optionally zlib-compress. Returns (data, compressed)."""
        raw = json.dumps(value, default=str).encode()
        if len(raw) > _COMPRESS_THRESHOLD:
            return zlib.compress(raw, level=6), True
        return raw, False

    @staticmethod
    def _deserialize(data: bytes, compressed: bool) -> Any:
        if compressed:
            data = zlib.decompress(data)
        return json.loads(data.decode())

    # ------------------------------------------------------------------
    # CacheBackend implementation
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        now = time.time()
        row = self._conn().execute(
            "SELECT value, compressed, expires_at FROM cache_entries WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < now:
            with self._write_lock:
                self._conn().execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                self._conn().commit()
            logger.debug("cache expired: %s", key)
            return None
        logger.debug("cache hit: %s", key)
        return self._deserialize(row["value"], bool(row["compressed"]))

    def set(self, key: str, value: Any, ttl: int) -> None:
        expires_at = time.time() + ttl
        data, compressed = self._serialize(value)
        with self._write_lock:
            self._conn().execute(
                "INSERT OR REPLACE INTO cache_entries (key, value, compressed, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (key, data, int(compressed), expires_at),
            )
            self._conn().commit()
        logger.debug("cache set: %s (ttl=%ds, compressed=%s, bytes=%d)", key, ttl, compressed, len(data))

    def invalidate(self, prefix: str) -> int:
        with self._write_lock:
            cur = self._conn().execute(
                "DELETE FROM cache_entries WHERE key = ? OR key LIKE ?",
                (prefix, f"{prefix}%"),
            )
            self._conn().commit()
        count = cur.rowcount
        if count:
            logger.debug("cache invalidated %d entries: prefix=%s", count, prefix)
        return count

    def list_entries(self) -> list[dict]:
        now = time.time()
        rows = self._conn().execute(
            "SELECT key, expires_at, length(value) as value_bytes, compressed"
            " FROM cache_entries WHERE expires_at > ? ORDER BY key",
            (now,),
        ).fetchall()
        entries = []
        for row in rows:
            key = row["key"]
            entries.append(
                {
                    "key": key,
                    "type": key.split(":")[0] if ":" in key else key,
                    "ttl_remaining_seconds": int(row["expires_at"] - now),
                    "value_bytes": row["value_bytes"],
                    "compressed": bool(row["compressed"]),
                }
            )
        return entries

    def clear_expired(self) -> int:
        now = time.time()
        with self._write_lock:
            cur = self._conn().execute(
                "DELETE FROM cache_entries WHERE expires_at < ?", (now,)
            )
            self._conn().commit()
        return cur.rowcount

    def clear_all(self) -> int:
        with self._write_lock:
            cur = self._conn().execute("DELETE FROM cache_entries")
            self._conn().commit()
        count = cur.rowcount
        logger.debug("cache cleared all %d entries", count)
        return count


# ---------------------------------------------------------------------------
# High-level NotebookCache (wraps backend, used throughout services)
# ---------------------------------------------------------------------------


class NotebookCache:
    """High-level cache used by services. Delegates to a backend.

    Usage::

        cache = get_cache()
        value = cache.get("notebook:abc123")
        cache.set("notebook:abc123", data, TTL["notebook"])
        cache.invalidate("notebook:abc123")
        cache.invalidate("notebook_list")   # exact key
    """

    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend

    def get(self, key: str) -> Any | None:
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._backend.set(key, value, ttl)

    def invalidate(self, prefix: str) -> int:
        return self._backend.invalidate(prefix)

    def list_entries(self) -> list[dict]:
        return self._backend.list_entries()

    def clear_expired(self) -> int:
        return self._backend.clear_expired()

    def clear_all(self) -> int:
        return self._backend.clear_all()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_cache: NotebookCache | None = None
_cache_init_lock = threading.Lock()


def get_cache() -> NotebookCache:
    """Return the process-wide cache singleton, creating it if needed."""
    global _cache
    if _cache is not None:
        return _cache
    with _cache_init_lock:
        if _cache is None:
            db_path = get_storage_dir() / "cache.db"
            backend = SQLiteCacheBackend(db_path)
            _cache = NotebookCache(backend)
    return _cache


def reset_cache() -> None:
    """Reset singleton (for testing)."""
    global _cache
    _cache = None
