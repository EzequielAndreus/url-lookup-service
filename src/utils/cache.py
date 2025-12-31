"""TTL-based in-memory caching utility for URL lookup results."""

from cachetools import TTLCache

from src.config import settings


class URLCache:
    """In-memory cache for URL lookup results with TTL and size limits."""

    def __init__(self, maxsize: int = 10000, ttl: int = 3600) -> None:
        """Initialize the cache.

        Args:
            maxsize: Maximum number of entries in the cache.
            ttl: Time-to-live in seconds for cache entries.
        """
        self.cache: TTLCache[str, bool] = TTLCache(maxsize=maxsize, ttl=ttl)
        self.enabled = settings.cache_enabled

    def get(self, url: str) -> bool | None:
        """Get a cached result for a URL.

        Args:
            url: The normalized URL to look up in cache.

        Returns:
            True/False if cached, None if not found or cache disabled.
        """
        if not self.enabled:
            return None

        try:
            return self.cache.get(url)
        except KeyError:
            return None

    def set(self, url: str, is_malicious: bool) -> None:
        """Cache a URL lookup result.

        Args:
            url: The normalized URL to cache.
            is_malicious: The lookup result (True if malicious).
        """
        if not self.enabled:
            return

        try:
            self.cache[url] = is_malicious
        except (KeyError, ValueError):
            # Cache full or other error; skip
            pass

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def size(self) -> int:
        """Get the current number of entries in the cache."""
        return len(self.cache)


# Global cache instance
url_cache = URLCache(maxsize=settings.cache_max_entries, ttl=settings.cache_ttl_seconds)
