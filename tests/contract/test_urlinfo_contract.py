"""Contract tests for the URL info endpoint.

Tests verify the API contract: request/response format, status codes, and required fields.
"""


def test_valid_url_returns_200(async_client):
    """T017: Valid URL returns 200 with all required response fields."""
    response = async_client.get("/urlinfo/1/example.com:80/")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields present
    assert "url" in data
    assert "is_malicious" in data
    assert "threat_level" in data
    assert "cached" in data
    assert "timestamp" in data
    assert "databases_queried" in data
    assert "response_time_ms" in data

    # Verify field types
    assert isinstance(data["url"], str)
    assert isinstance(data["is_malicious"], bool)
    assert isinstance(data["threat_level"], str)
    assert isinstance(data["cached"], bool)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["databases_queried"], list)
    assert isinstance(data["response_time_ms"], (int, float))


def test_malware_url_detected(async_client):
    """T018: Known malicious URL returns is_malicious=true."""
    # Use a URL from our test fixtures (example.com is in sample_malware_urls.csv)
    response = async_client.get("/urlinfo/1/example.com:80/")

    assert response.status_code == 200
    data = response.json()

    # example.com is in the malware list
    assert data["is_malicious"] is True
    assert data["threat_level"] in ["high", "critical"]


def test_safe_url_not_detected(async_client):
    """T019: Known safe URL returns is_malicious=false."""
    # Use a URL not in our malware list
    response = async_client.get("/urlinfo/1/google.com:80/")

    assert response.status_code == 200
    data = response.json()

    # google.com is not in the malware list
    assert data["is_malicious"] is False
    assert data["threat_level"] == "safe"


def test_response_headers_present(async_client):
    """T020: Response includes required headers."""
    response = async_client.get("/urlinfo/1/example.com:80/")

    assert response.status_code == 200

    # Verify required headers
    assert "x-request-id" in response.headers
    assert "content-type" in response.headers

    # Verify header values
    assert response.headers["x-request-id"].startswith("req-")
    assert "application/json" in response.headers["content-type"]


def test_health_check_endpoint(async_client):
    """Health check endpoint returns service status."""
    response = async_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Should have basic status info
    assert "status" in data or "ready" in data
    assert "loaders" in data or "service" in data or "url" in data
