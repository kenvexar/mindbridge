"""LRU Cache implementation for memory optimization."""

import time
from collections import OrderedDict
from collections.abc import Sized
from threading import RLock
from typing import Any, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache[K, V]:
    """Thread-safe LRU (Least Recently Used) cache implementation."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float | None = None):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to store
            ttl_seconds: Time-to-live in seconds (None for no expiration)
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")

        self._cache: OrderedDict[K, tuple[V, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = RLock()

    def get(self, key: K, default: V | None = None) -> V | None:
        """
        Get value by key, moving it to end (most recently used).

        Args:
            key: Cache key
            default: Default value if not found or expired

        Returns:
            Cached value or default
        """
        with self._lock:
            if key not in self._cache:
                return default

            value, timestamp = self._cache[key]

            # Check TTL expiration
            if self._ttl_seconds and time.time() - timestamp > self._ttl_seconds:
                del self._cache[key]
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def put(self, key: K, value: V) -> None:
        """
        Store key-value pair, evicting oldest if necessary.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            current_time = time.time()

            # Update existing key
            if key in self._cache:
                self._cache[key] = (value, current_time)
                self._cache.move_to_end(key)
                return

            # Evict oldest entries if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key, _ = self._cache.popitem(last=False)

            # Add new entry
            self._cache[key] = (value, current_time)

    def delete(self, key: K) -> bool:
        """
        Delete key from cache.

        Args:
            key: Key to delete

        Returns:
            True if key existed and was deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def __len__(self) -> int:
        """Support len() function for Sized protocol."""
        return self.size()

    def is_full(self) -> bool:
        """Check if cache is at maximum capacity."""
        with self._lock:
            return len(self._cache) >= self._max_size

    def cleanup_expired(self) -> int:
        """
        Remove expired entries if TTL is enabled.

        Returns:
            Number of expired entries removed
        """
        if not self._ttl_seconds:
            return 0

        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, (_, timestamp) in self._cache.items():
                if current_time - timestamp > self._ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "usage_ratio": len(self._cache) / self._max_size,
                "is_full": self.is_full(),
                "ttl_seconds": self._ttl_seconds,
            }


class MemoryOptimizedCache(LRUCache[str, Any], Sized):
    """Specialized LRU cache for AI processing with memory optimization."""

    def __init__(self, max_size: int = 500, ttl_hours: float = 24.0):
        """
        Initialize memory-optimized cache.

        Args:
            max_size: Maximum cache entries (reduced from unlimited)
            ttl_hours: Cache expiration time in hours
        """
        super().__init__(max_size, ttl_hours * 3600)
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get with hit/miss tracking."""
        result = super().get(key, default)

        if result is not default:
            self._hit_count += 1
        else:
            self._miss_count += 1

        return result

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Performance metrics including hit ratio
        """
        total_requests = self._hit_count + self._miss_count
        hit_ratio = self._hit_count / total_requests if total_requests > 0 else 0.0

        base_stats = self.get_stats()
        base_stats.update(
            {
                "hits": self._hit_count,
                "misses": self._miss_count,
                "hit_ratio": hit_ratio,
                "total_requests": total_requests,
            }
        )

        return base_stats

    def reset_stats(self) -> None:
        """Reset performance counters."""
        self._hit_count = 0
        self._miss_count = 0
