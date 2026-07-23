"""Simple TTL cache for hot-read DB calls.
Used by agent tools to avoid repeated DB round trips.
"""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """Dict-based TTL cache. Not thread-safe — use one per event loop."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, Any] = {}
        self._times: dict[str, float] = {}

    def _key(self, *args: str) -> str:
        return ":".join(str(a) for a in args)

    def get(self, *args: str) -> Any | None:
        key = self._key(*args)
        val = self._data.get(key)
        if val is None:
            return None
        if time.monotonic() - self._times.get(key, 0) > self._ttl:
            self._data.pop(key, None)
            self._times.pop(key, None)
            return None
        return val

    def set(self, *args: str, value: Any) -> None:
        key = self._key(*args)
        self._data[key] = value
        self._times[key] = time.monotonic()

    def invalidate(self, *args: str) -> None:
        key = self._key(*args)
        self._data.pop(key, None)
        self._times.pop(key, None)

    def clear(self) -> None:
        self._data.clear()
        self._times.clear()


# ponytail: global cache instance, per-tenant isolation if needed
stock_cache = TTLCache(ttl_seconds=30.0)
supplier_cache = TTLCache(ttl_seconds=30.0)
