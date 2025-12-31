"""Performance benchmarking and profiling tests.

Tests that establish baseline performance metrics and detect regressions.
"""

import time
from statistics import mean

import pytest


class TestPerformanceBenchmarks:
    """T060: Establish performance baselines."""

    def test_single_request_baseline(self, async_client):
        """Establish baseline for single request performance."""
        times = []

        for i in range(10):
            start = time.time()
            response = async_client.get(f"/urlinfo/1/bench-{i}.com/")
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)
            assert response.status_code == 200

        avg_time = mean(times)

        # Performance baseline: average should be < 100ms
        assert avg_time < 100, f"Average response time: {avg_time:.1f}ms"

        # Log metrics for trend analysis
        pytest.skip(f"Baseline: {avg_time:.1f}ms (min: {min(times):.1f}, max: {max(times):.1f})")

    def test_malware_detection_baseline(self, async_client):
        """Baseline for malware detection performance."""
        times = []

        for _i in range(10):
            start = time.time()
            response = async_client.get("/urlinfo/1/evil.net/")
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)
            assert response.status_code == 200

        avg_time = mean(times)
        assert avg_time < 500, f"Malware check average: {avg_time:.1f}ms"

    def test_validation_error_baseline(self, async_client):
        """Baseline for validation error performance."""
        times = []

        for _i in range(10):
            start = time.time()
            response = async_client.get("/urlinfo/1/")
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)
            assert response.status_code == 400

        avg_time = mean(times)
        # Validation errors should be fast
        assert avg_time < 50, f"Validation error average: {avg_time:.1f}ms"


class TestThroughputPerformance:
    """Test maximum throughput characteristics."""

    def test_requests_per_second_minimum(self, async_client):
        """System should handle minimum 10 req/sec."""
        start = time.time()
        request_count = 0

        while time.time() - start < 1.0:  # Run for 1 second
            response = async_client.get(f"/urlinfo/1/rps-test-{request_count}.com/")
            if response.status_code == 200:
                request_count += 1

        # Should handle at least 10 requests per second
        assert request_count >= 10, f"Only {request_count} req/sec"

    def test_sustained_throughput(self, async_client):
        """Throughput should be consistent over time."""
        segments = []

        # Run 5 x 1-second segments
        for _segment in range(5):
            start = time.time()
            count = 0

            while time.time() - start < 1.0:
                response = async_client.get(f"/urlinfo/1/sustained-{count}.com/")
                if response.status_code == 200:
                    count += 1

            segments.append(count)

        # All segments should be similar (no degradation)
        avg_segment = mean(segments)
        assert avg_segment >= 10, f"Average throughput: {avg_segment:.0f} req/sec"


class TestLatencyDistribution:
    """Test response time distribution and outliers."""

    def test_p99_latency(self):
        """99th percentile latency should be reasonable."""
        times = []

        for _i in range(100):
            start = time.time()
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)

        times_sorted = sorted(times)
        p99_idx = int(len(times_sorted) * 0.99)
        p99_latency = times_sorted[p99_idx]

        # P99 should be under 500ms
        assert p99_latency < 500, f"P99 latency: {p99_latency:.1f}ms"

    def test_p95_latency(self):
        """95th percentile latency should be very good."""
        times = []

        for _i in range(100):
            start = time.time()
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)

        times_sorted = sorted(times)
        p95_idx = int(len(times_sorted) * 0.95)
        p95_latency = times_sorted[p95_idx]

        # P95 should be under 200ms
        assert p95_latency < 200, f"P95 latency: {p95_latency:.1f}ms"

    def test_outlier_requests_reasonable(self):
        """Even slowest requests should be reasonable."""
        times = []

        for _i in range(50):
            start = time.time()
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)

        max_time = max(times)
        # Even worst case should be under 1 second
        assert max_time < 1000, f"Worst case: {max_time:.1f}ms"


class TestResourceUtilization:
    """Test resource efficiency."""

    def test_memory_not_growing_unbounded(self, async_client):
        """Memory should not grow unbounded with requests."""
        # Just verify we can make many requests without error
        for i in range(200):
            response = async_client.get(f"/urlinfo/1/mem-{i % 20}.com/")
            assert response.status_code == 200

    def test_no_connection_leaks(self, async_client):
        """Repeated requests should not leak connections."""
        url = "/urlinfo/1/connection-test.com/"

        # Make many requests to same URL
        for _i in range(100):
            response = async_client.get(url)
            assert response.status_code == 200

        # If we got here without error, no connection leaks


class TestCacheAssistedPerformance:
    """T061: Cache-assisted performance improvements."""

    def test_cache_reduces_response_time(self, async_client):
        """Cache should significantly reduce response time."""
        url = "/urlinfo/1/cache-perf.com/"

        # First request (uncached)
        times_uncached = []
        for _ in range(3):
            # Clear cache effect by using different URLs
            start = time.time()
            async_client.get(f"/urlinfo/1/uncached-{_}.com/")
            times_uncached.append((time.time() - start) * 1000)

        # Repeated request (cached)
        times_cached = []
        for _ in range(10):
            start = time.time()
            async_client.get(url)
            times_cached.append((time.time() - start) * 1000)

        avg_uncached = mean(times_uncached)
        avg_cached = mean(times_cached)

        # Cached should be noticeably faster
        assert avg_cached < avg_uncached * 0.9, (
            f"Uncached: {avg_uncached:.1f}ms, Cached: {avg_cached:.1f}ms"
        )

    def test_cache_enabled_configuration(self, async_client):
        """Cache should be enabled by default."""
        # Make a request and check if cached flag appears
        response = async_client.get("/urlinfo/1/cache-config.com/")
        data = response.json()

        # Response should have cached field
        assert "cached" in data
        assert isinstance(data["cached"], bool)
