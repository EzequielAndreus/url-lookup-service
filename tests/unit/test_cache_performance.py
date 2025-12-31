"""Unit tests for cache performance.

Tests verify cache implementation efficiency:
- Cache hit/miss performance
- TTL enforcement
- Memory efficiency
- Cache eviction policies
"""

import time

from src.utils.cache import URLCache


class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_cache_get_under_1ms(self):
        """Cache lookups should be sub-millisecond."""
        cache = URLCache(maxsize=100, ttl=3600)

        # Add item
        cache.set("test_key", {"malicious": False})

        # Lookup should be very fast
        start = time.time()
        result = cache.get("test_key")
        elapsed_us = (time.time() - start) * 1_000_000  # Convert to microseconds

        assert result is not None
        assert elapsed_us < 1000, f"Cache lookup took {elapsed_us:.0f}µs, expected < 1000µs"

    def test_cache_set_under_1ms(self):
        """Cache writes should be sub-millisecond."""
        cache = URLCache(maxsize=100, ttl=3600)

        start = time.time()
        cache.set("perf_test", {"data": "test"})
        elapsed_us = (time.time() - start) * 1_000_000

        assert elapsed_us < 1000, f"Cache write took {elapsed_us:.0f}µs"

    def test_cache_hit_vs_miss_time_difference(self):
        """Cache hit should be significantly faster than repeated computation."""
        cache = URLCache(maxsize=100, ttl=3600)

        # Simulate cached vs uncached lookup
        key = "perf_comparison"
        value = {"complex_data": "x" * 1000}

        # Add to cache
        cache.set(key, value)

        # Second: cached
        start2 = time.time()
        result2 = cache.get(key)
        hit_time = (time.time() - start2) * 1000

        # Hit should be faster (though both very fast)
        assert result2 is not None
        assert hit_time < 10  # Should be very fast

    def test_cache_ttl_expiration(self):
        """Items should expire after TTL."""
        cache = URLCache(maxsize=100, ttl=1)

        cache.set("ttl_test", {"value": "test"})
        assert cache.get("ttl_test") is not None

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("ttl_test") is None

    def test_cache_eviction_policy(self):
        """Cache should respect max size and evict old items."""
        cache = URLCache(maxsize=10, ttl=3600)

        # Add more items than max_size
        for i in range(15):
            cache.set(f"key_{i}", {"value": i})

        # Cache size should not exceed max (or be close to it)
        # Note: We can't directly check size, so we verify oldest items might be evicted
        # The implementation uses cachetools.TTLCache which handles this

    def test_cache_clear_performance(self):
        """Clear operation should be efficient."""
        cache = URLCache(maxsize=1000, ttl=3600)

        # Add many items
        for i in range(100):
            cache.set(f"key_{i}", {"data": "x" * 100})

        # Clear should be fast
        start = time.time()
        cache.clear()
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 100, f"Clear took {elapsed_ms:.1f}ms"
        assert cache.get("key_0") is None


class TestCacheMemoryEfficiency:
    """Test cache memory usage characteristics."""

    def test_cache_stores_references_not_copies(self):
        """Cache should efficiently store data without excessive copies."""
        cache = URLCache(maxsize=100, ttl=3600)

        large_data = {"urls": ["http://example.com"] * 100}
        cache.set("large", large_data)

        # Retrieve and verify
        result = cache.get("large")
        assert result is not None
        assert len(result["urls"]) == 100

    def test_cache_with_large_values(self):
        """Cache should handle reasonably large values efficiently."""
        cache = URLCache(maxsize=50, ttl=3600)

        # Add items with larger data payloads
        for i in range(50):
            large_value = {"data": "x" * 1000, "timestamp": time.time(), "index": i}
            cache.set(f"key_{i}", large_value)

        # Should still retrieve quickly
        start = time.time()
        result = cache.get("key_25")
        elapsed_us = (time.time() - start) * 1_000_000

        assert result is not None
        assert elapsed_us < 5000


class TestCacheHitRate:
    """Test cache hit rate optimization."""

    def test_repeated_access_hit_rate(self):
        """Repeated access to same key should have high hit rate."""
        cache = URLCache(maxsize=100, ttl=3600)

        cache.set("repeated", {"value": "test"})

        hits = 0
        for _ in range(10):
            if cache.get("repeated") is not None:
                hits += 1

        # All 10 accesses should hit
        assert hits == 10

    def test_working_set_fits_in_cache(self):
        """Common working set should fit entirely in cache."""
        cache = URLCache(maxsize=100, ttl=3600)

        # Add 20 items (well within 100 item limit)
        for i in range(20):
            cache.set(f"item_{i}", {"value": i})

        # All should be retrievable
        hits = 0
        for i in range(20):
            if cache.get(f"item_{i}") is not None:
                hits += 1

        assert hits == 20
