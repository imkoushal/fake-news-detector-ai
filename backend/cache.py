"""
Thread-safe TTL-based in-memory LRU cache for API verification results.
Prevents redundant external API calls for repeated viral claims.
"""
import hashlib
import time
import threading
from collections import OrderedDict


class ClaimCache:
    """TTL-based in-memory cache for API verification results.
    Keyed by normalized text hash. Auto-evicts oldest when full.
    Thread-safe via threading.Lock.
    """
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def _normalize_key(self, text: str, endpoint: str) -> str:
        """Create a stable cache key from text + endpoint."""
        normalized = " ".join(text.lower().split())[:1000]
        raw = f"{endpoint}:{normalized}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, text: str, endpoint: str):
        """Return cached result copy or None if miss/expired."""
        key = self._normalize_key(text, endpoint)
        with self._lock:
            if key in self._cache:
                ts, data = self._cache[key]
                if time.time() - ts < self._ttl:
                    self._hits += 1
                    self._cache.move_to_end(key)
                    return {**data}  # Return a copy to avoid mutation
                else:
                    del self._cache[key]
            self._misses += 1
        return None

    def set(self, text: str, endpoint: str, data: dict):
        """Store a result in the cache."""
        key = self._normalize_key(text, endpoint)
        with self._lock:
            self._cache[key] = (time.time(), data)
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "cache_size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
                "total_requests": total,
            }

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
