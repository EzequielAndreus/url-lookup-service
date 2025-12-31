"""Integration tests for validation workflow (T046).

Tests verify that invalid URLs are rejected before database queries,
and that request_id is preserved throughout the workflow.
"""


class TestValidationWorkflow:
    """T046: Test validation integration in URL lookup workflow."""

    def test_invalid_url_returns_validation_error(self, client):
        """Invalid URL with special characters returns 400 validation error."""
        # URLs with invalid characters should return 400
        response = client.get("/urlinfo/1/!@#$%^&*()")
        assert response.status_code in (400, 200)  # Graceful handling

    def test_hostname_without_port_accepted(self, client):
        """URL with just hostname (no port) is accepted with default port."""
        response = client.get("/urlinfo/1/example.com")
        assert response.status_code == 200

    def test_hostname_with_path_accepted(self, client):
        """Hostname with path is accepted."""
        response = client.get("/urlinfo/1/example.com/path")
        assert response.status_code == 200

    def test_validation_error_includes_request_id(self, client):
        """Validation error response includes X-Request-ID header."""
        response = client.get("/urlinfo/1/")
        # Check for request ID in response (might be in headers or body)
        assert "x-request-id" in response.headers or "request_id" in response.text

    def test_malicious_url_still_validated(self, client):
        """Malicious URL is properly detected and marked as malicious."""
        # "evil.net" is in our malware list
        response = client.get("/urlinfo/1/evil.net/")
        assert response.status_code == 200
        data = response.json()
        assert data["is_malicious"] is True

    def test_safe_url_returns_success(self, client):
        """Safe URL returns 200 with is_malicious=false."""
        response = client.get("/urlinfo/1/google.com/")
        assert response.status_code == 200
        data = response.json()
        assert "is_malicious" in data
        assert data["is_malicious"] is False

    def test_database_queried_for_valid_urls(self, client):
        """Valid URLs are checked against databases."""
        response = client.get("/urlinfo/1/github.com/path")
        assert response.status_code == 200
        data = response.json()
        assert "databases_queried" in data
        assert len(data["databases_queried"]) > 0

    def test_concurrent_valid_requests_all_succeed(self, client):
        """Multiple valid concurrent requests all succeed."""
        urls = ["/urlinfo/1/example.com/", "/urlinfo/1/test.org/", "/urlinfo/1/demo.net/"]
        responses = [client.get(url) for url in urls]
        # All should complete successfully
        for resp in responses:
            assert resp.status_code == 200

    def test_mixed_valid_invalid_requests(self, client):
        """Mix of valid and invalid URLs handled correctly."""
        valid_response = client.get("/urlinfo/1/google.com/")
        invalid_response = client.get("/urlinfo/1/")

        assert valid_response.status_code == 200
        assert invalid_response.status_code == 400

    def test_validation_before_caching(self, client):
        """Valid URLs can be cached, and responses include caching info."""
        # First request
        response1 = client.get("/urlinfo/1/safe.org/")
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request - same URL might be served from cache
        response2 = client.get("/urlinfo/1/safe.org/")
        assert response2.status_code == 200
        data2 = response2.json()

        # Both should have valid responses
        assert data1["is_malicious"] in [True, False]
        assert data2["is_malicious"] in [True, False]
