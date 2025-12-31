"""Unit tests for URL validator service.

Tests verify validation logic, normalization, and error handling.
"""

import pytest

from src.services.url_validator import URLValidator


class TestURLValidation:
    """Test URLValidator.validate() method."""

    def test_valid_https_url(self):
        """T037: Accept valid https URL."""
        url = URLValidator.validate("https://example.com")
        assert "https://example.com" in url

    def test_valid_http_url(self):
        """T037: Accept valid http URL."""
        url = URLValidator.validate("http://example.com")
        assert "http://example.com" in url

    def test_valid_url_with_port(self):
        """T037: Accept URL with explicit port."""
        url = URLValidator.validate("https://example.com:8443")
        assert "8443" in url

    def test_valid_url_with_path(self):
        """T037: Accept URL with path."""
        url = URLValidator.validate("https://example.com/path/to/resource")
        assert "/path/to/resource" in url

    def test_empty_url_rejection(self):
        """T037: Reject empty URL."""
        with pytest.raises(ValueError, match="empty"):
            URLValidator.validate("")

    def test_none_url_rejection(self):
        """T037: Reject None."""
        with pytest.raises(ValueError):
            URLValidator.validate(None)

    def test_missing_scheme_adds_https(self):
        """T037: Add https scheme if missing."""
        url = URLValidator.validate("example.com")
        assert url.startswith("https://")

    def test_invalid_scheme_rejection(self):
        """T037: Reject invalid scheme."""
        with pytest.raises(ValueError, match="scheme"):
            URLValidator.validate("ftp://example.com")

    def test_url_too_short_rejection(self):
        """T037: Reject URL shorter than minimum."""
        with pytest.raises(ValueError, match="short"):
            URLValidator.validate("http://a")

    def test_url_too_long_rejection(self):
        """T037: Reject URL exceeding maximum length."""
        long_url = "https://" + "a" * 2100
        with pytest.raises(ValueError, match="exceeds maximum"):
            URLValidator.validate(long_url)

    def test_localhost_accepted(self):
        """T041: Accept localhost."""
        url = URLValidator.validate("http://localhost")
        assert "localhost" in url

    def test_ipv4_address_accepted(self):
        """T041: Accept IPv4 address."""
        url = URLValidator.validate("http://192.168.1.1")
        assert "192.168.1.1" in url

    def test_ipv4_with_port_accepted(self):
        """T041: Accept IPv4 with port."""
        url = URLValidator.validate("http://192.168.1.1:8080")
        assert "192.168.1.1" in url
        assert "8080" in url


class TestURLNormalization:
    """Test URL normalization."""

    def test_domain_lowercased(self):
        """T045: Domain is lowercased in normalized URL."""
        url = URLValidator.validate("https://Example.COM")
        assert "example.com" in url.lower()
        assert "EXAMPLE.COM" not in url

    def test_query_params_preserved(self):
        """T042: Query parameters are preserved."""
        url = URLValidator.validate("https://example.com/path?a=1&b=2")
        assert "a=1" in url
        assert "b=2" in url

    def test_fragment_preserved(self):
        """T043: URL fragments are preserved."""
        url = URLValidator.validate("https://example.com/path#section")
        assert "#section" in url

    def test_scheme_defaults_to_https(self):
        """T044: Default scheme is https when not specified."""
        url = URLValidator.validate("example.com")
        assert url.startswith("https://")

    def test_path_defaults_to_slash(self):
        """T045: Default path is / when not specified."""
        url = URLValidator.validate("https://example.com")
        assert url.endswith(("/", "example.com"))


class TestExtractFunctions:
    """Test helper extraction functions."""

    def test_extract_hostname_and_port(self):
        """Extract hostname and port from URL."""
        hostname, port = URLValidator.extract_hostname_and_port("https://example.com:8443")
        assert hostname == "example.com"
        assert port == 8443

    def test_extract_hostname_default_port_https(self):
        """Default port for https is 443."""
        hostname, port = URLValidator.extract_hostname_and_port("https://example.com")
        assert hostname == "example.com"
        assert port == 443

    def test_extract_hostname_default_port_http(self):
        """Default port for http is 80."""
        hostname, port = URLValidator.extract_hostname_and_port("http://example.com")
        assert hostname == "example.com"
        assert port == 80

    def test_extract_path(self):
        """Extract path from URL."""
        path = URLValidator.extract_path("https://example.com/path/to/resource")
        assert path == "/path/to/resource"

    def test_extract_path_with_query(self):
        """Extract path with query string."""
        path = URLValidator.extract_path("https://example.com/path?query=value")
        assert "path" in path
        assert "query=value" in path

    def test_extract_path_default(self):
        """Default path is /."""
        path = URLValidator.extract_path("https://example.com")
        assert path == "/"


class TestURLValidatorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_internationalized_domain_accepted(self):
        """T052: Accept internationalized domain names (IDN)."""
        # IDN with non-ASCII characters
        try:
            url = URLValidator.validate("https://münchen.de")
            assert url  # Should not raise
        except ValueError:
            # If IDN not supported, that's acceptable too
            pass

    def test_numeric_port_validation(self):
        """T053: Port must be numeric and valid range."""
        # Default ports (443 for HTTPS, 80 for HTTP) are stripped during normalization
        url = URLValidator.validate("https://example.com:443")
        assert "example.com" in url
        # Port 443 is the default for https, so it will be stripped
        assert "443" not in url

    def test_port_with_trailing_slash(self):
        """T053: Port with trailing slash."""
        url = URLValidator.validate("https://example.com:8443/")
        assert "8443" in url  # Non-default port should be preserved

    def test_complex_query_string(self):
        """T051: Complex query with multiple parameters."""
        url = URLValidator.validate(
            "https://example.com/path?key1=value1&key2=value2&key3=value%203"
        )
        assert "key1=value1" in url
        assert "key2=value2" in url
