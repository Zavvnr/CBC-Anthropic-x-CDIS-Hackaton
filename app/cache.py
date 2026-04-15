"""
cache.py — In-memory LRU cache with per-entry TTL.

Think of this like a sticky-note board with an expiry timer on each note:
the board only keeps the N most-recently used notes, and any note older
than its timer is silently discarded when you next look at it.
"""

import time
import threading
from collections import OrderedDict
from typing import Any, Optional


# Sentinel so callers can distinguish a cached None from a cache miss.
_MISSING = object()


class TTLLRUCache:
    """
    Thread-safe LRU cache where every entry expires after `ttl_seconds`.

    Complexity: O(1) get and set via OrderedDict.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: float = 30.0) -> None:
        """Initialise cache with capacity and time-to-live per entry."""
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        # OrderedDict preserves insertion order; we move accessed keys to the end.
        self._store: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, key: Any) -> Any:
        """Return cached value for key, or _MISSING if absent or expired."""
        with self._lock:
            return self._get_unlocked(key)

    def set(self, key: Any, value: Any) -> None:
        """Store value under key, evicting the oldest entry if at capacity."""
        with self._lock:
            expiry_time = time.monotonic() + self._ttl_seconds
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expiry_time)
            if len(self._store) > self._max_size:
                self._store.popitem(last=False)  # evict least-recently used

    def invalidate(self, key: Any) -> None:
        """Remove a single entry from the cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Flush all entries — useful after bulk writes."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        """Return the number of unexpired entries currently held."""
        with self._lock:
            now = time.monotonic()
            return sum(1 for _, expiry in self._store.values() if expiry > now)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_unlocked(self, key: Any) -> Any:
        """Perform a get without acquiring the lock (caller must hold it)."""
        entry = self._store.get(key, None)
        if entry is None:
            return _MISSING

        value, expiry_time = entry
        if time.monotonic() > expiry_time:
            del self._store[key]
            return _MISSING

        # Promote to most-recently used position.
        self._store.move_to_end(key)
        return value


# Module-level singleton used by the matching engine.
# TTL and size are overridden from env vars in main.py after config loads.
match_cache = TTLLRUCache(max_size=512, ttl_seconds=30.0)

MISSING = _MISSING  # Re-exported so callers can do `from app.cache import MISSING`
