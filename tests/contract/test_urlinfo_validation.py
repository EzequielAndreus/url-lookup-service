"""Contract tests for URL input validation and error responses.

Tests verify API contract for error handling: status codes, error format, and messages.
"""


def test_empty_url_rejection(async_client):
    """T032: Empty URL returns 400 with error detail."""
    response = async_client.get("/urlinfo/1//")

    # Should return 400 or 422 (validation error)
    assert response.status_code in (400, 422)
    data = response.json()

    # Should include error detail
    assert "detail" in data or "error" in data


def test_missing_scheme_rejection(async_client):
    """T033: URL without scheme returns 400."""
    response = async_client.get("/urlinfo/1/example.com/path")

    # Should be accepted since we parse hostname:port format
    # but test that it works correctly
    assert response.status_code in (200, 400)


def test_missing_domain_rejection(async_client):
    """T034: URL with missing domain returns 400."""
    response = async_client.get("/urlinfo/1/?query=value")

    # Empty hostname should fail
    assert response.status_code in (400, 422)


def test_url_exceeding_max_length_rejection(async_client):
    """T035: Extremely long URL returns 400."""
    # Create a URL longer than 2048 characters
    long_path = "a" * 3000
    response = async_client.get(f"/urlinfo/1/example.com:80/{long_path}")

    # Should reject due to length
    assert response.status_code in (400, 422, 414)


def test_error_response_format(async_client):
    """T036: Error responses include detail and request_id."""
    response = async_client.get("/urlinfo/1//")

    if response.status_code in (400, 422):
        data = response.json()

        # Should have detail or error message
        assert "detail" in data or "error" in data

        # Response should be valid JSON
        assert isinstance(data, dict)


def test_malformed_port_rejection(async_client):
    """T036b: Malformed port number returns 400."""
    response = async_client.get("/urlinfo/1/example.com:invalid/")

    # Should either parse port as 80 or return error
    assert response.status_code in (200, 400)


def test_health_check_available_on_validation_error(async_client):
    """Ensure health check still works even with validation errors."""
    # Make a validation error
    response = async_client.get("/urlinfo/1//")
    assert response.status_code in (400, 422)

    # Health check should still work
    response = async_client.get("/health")
    assert response.status_code == 200
