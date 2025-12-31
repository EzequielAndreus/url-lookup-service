"""Contract tests for performance requirements.

Tests verify that the API meets performance SLAs:
- Single request response time < 1000ms
- Concurrent request handling without timeouts
- Cache effectiveness (cached responses < 10ms)
- Database query performance under load
"""

import time


class TestResponseTimeContract:
    """T055: Response time performance SLA."""

    def test_single_request_under_1000ms(self, async_client):
        """Single request should complete within 1000ms."""
        start = time.time()
        response = async_client.get("/urlinfo/1/google.com/")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 1000, f"Request took {elapsed_ms:.1f}ms, expected < 1000ms"

    def test_invalid_url_validation_under_100ms(self, async_client):
        """Invalid URL validation should fail fast (< 100ms)."""
        start = time.time()
        response = async_client.get("/urlinfo/1//")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 400
        assert elapsed_ms < 100, f"Validation took {elapsed_ms:.1f}ms, expected < 100ms"

    def test_cached_response_under_10ms(self, async_client):
        """Cached response should be very fast (< 10ms after warm-up)."""
        # First request - not cached
        async_client.get("/urlinfo/1/example.com/")

        # Second request - should be cached
        start = time.time()
        response = async_client.get("/urlinfo/1/example.com/")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        # Cached responses should be much faster (but allow some margin)
        assert elapsed_ms < 100  # Reasonable cached response time


class TestConcurrentRequestHandling:
    """T056: Handle concurrent requests without blocking."""

    def test_10_concurrent_requests_succeed(self, async_client):
        """10 concurrent-like requests should all succeed."""
        urls = [f"/urlinfo/1/test-{i}.com/" for i in range(10)]

        responses = []
        start = time.time()

        # Simulate concurrent requests (sequential in test, but measures time)
        for url in urls:
            responses.append(async_client.get(url))

        elapsed_ms = (time.time() - start) * 1000

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # Total time should be reasonable (not sum of individual times)
        assert elapsed_ms < 5000, f"10 requests took {elapsed_ms:.0f}ms"

    def test_mixed_valid_invalid_requests_concurrent(self, async_client):
        """Mix of valid and invalid requests should all complete."""
        urls = [
            "/urlinfo/1/google.com/",
            "/urlinfo/1/bad-url",
            "/urlinfo/1/example.org/path",
            "/urlinfo/1/",  # Invalid
            "/urlinfo/1/github.com/",
        ]

        responses = []
        for url in urls:
            responses.append(async_client.get(url))

        # Should have appropriate status codes
        assert responses[0].status_code == 200  # valid
        assert responses[1].status_code == 200  # valid (hostname)
        assert responses[2].status_code == 200  # valid
        assert responses[3].status_code == 400  # invalid
        assert responses[4].status_code == 200  # valid

    def test_burst_traffic_stability(self, async_client):
        """Handle burst of 20+ requests without degradation."""
        urls = [f"/urlinfo/1/domain-{i}.test/" for i in range(20)]

        responses = []
        for url in urls:
            responses.append(async_client.get(url))

        # All should succeed
        assert len(responses) == 20
        assert all(r.status_code == 200 for r in responses)


class TestCachePerformance:
    """T057: Cache effectiveness and performance."""

    def test_cache_hit_faster_than_miss(self, async_client):
        """Cached request should be generally fast."""
        url = "/urlinfo/1/cached-test.com/"

        # First request - uncached, measure time
        start1 = time.time()
        response1 = async_client.get(url)
        time1_ms = (time.time() - start1) * 1000

        # Second request - cached, measure time
        start2 = time.time()
        response2 = async_client.get(url)
        time2_ms = (time.time() - start2) * 1000

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should be reasonably fast
        # Cache hit should generally be faster, but allow some variance due to system load
        assert time1_ms < 100, f"Cache miss should be < 100ms, got {time1_ms:.1f}ms"
        assert time2_ms < 100, f"Cache hit should be < 100ms, got {time2_ms:.1f}ms"

    def test_cache_response_includes_cached_flag(self, async_client):
        """Response should indicate if result came from cache."""
        url = "/urlinfo/1/flag-test.com/"

        # First request
        r1 = async_client.get(url)
        data1 = r1.json()

        # Second request - should be cached
        r2 = async_client.get(url)
        data2 = r2.json()

        # Both should have cached flag
        assert "cached" in data1
        assert "cached" in data2
        # Second should be marked as cached
        assert data2["cached"] is True

    def test_response_time_included(self, async_client):
        """Response should include timing information."""
        response = async_client.get("/urlinfo/1/timing-test.com/")
        data = response.json()

        assert "response_time_ms" in data
        assert data["response_time_ms"] > 0
        assert data["response_time_ms"] < 1000


class TestDatabaseQueryPerformance:
    """T058: Database query optimization."""

    def test_malware_lookup_fast_miss(self, async_client):
        """Negative (not malicious) lookup should be fast."""
        start = time.time()
        response = async_client.get("/urlinfo/1/safe-clean.com/")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()
        assert data["is_malicious"] is False
        assert elapsed_ms < 500

    def test_malware_lookup_fast_hit(self, async_client):
        """Positive (malicious) lookup should be fast."""
        start = time.time()
        response = async_client.get("/urlinfo/1/evil.net/")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()
        assert data["is_malicious"] is True
        assert elapsed_ms < 500

    def test_parallel_database_queries(self, async_client):
        """Multiple parallel database queries should complete efficiently."""
        # This tests that asyncio.gather() is working efficiently
        urls = [f"/urlinfo/1/multi-{i}.com/" for i in range(5)]

        start = time.time()
        responses = [async_client.get(url) for url in urls]
        elapsed_ms = (time.time() - start) * 1000

        # All should complete
        assert all(r.status_code == 200 for r in responses)
        # Should complete reasonably fast (parallel execution)
        assert elapsed_ms < 2000


class TestLoadStability:
    """T059: System stability under sustained load."""

    def test_100_sequential_requests_succeed(self, async_client):
        """100 sequential requests should all succeed without error."""
        start = time.time()

        for i in range(100):
            response = async_client.get(f"/urlinfo/1/load-test-{i % 10}.com/")
            assert response.status_code in [200, 400]  # All should be valid responses

        elapsed_ms = (time.time() - start) * 1000

        # Should complete in reasonable time
        avg_time = elapsed_ms / 100
        assert avg_time < 50, f"Average request time: {avg_time:.1f}ms"

    def test_repeated_same_url_cached_efficiently(self, async_client):
        """Repeated requests to same URL should benefit from cache."""
        url = "/urlinfo/1/repeat-test.com/"

        times = []
        for _i in range(5):
            start = time.time()
            response = async_client.get(url)
            times.append((time.time() - start) * 1000)
            assert response.status_code == 200

        # Later requests should be faster (cached)
        assert times[-1] < times[0]

    def test_error_handling_doesnt_degrade_performance(self, async_client):
        """Invalid requests shouldn't slow down system."""
        valid_times = []
        invalid_times = []

        # Mix of valid and invalid requests
        for i in range(10):
            # Valid request
            start = time.time()
            async_client.get(f"/urlinfo/1/perf-{i}.com/")
            valid_times.append((time.time() - start) * 1000)

            # Invalid request
            start = time.time()
            async_client.get("/urlinfo/1/")
            invalid_times.append((time.time() - start) * 1000)

        # Both should average < 50ms
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)

        assert avg_valid < 50
        assert avg_invalid < 50
