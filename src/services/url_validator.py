"""URL validation and normalization service."""

from urllib.parse import ParseResult, urlparse

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Constants
MAX_URL_LENGTH = 2048
MIN_URL_LENGTH = 10
VALID_SCHEMES = {"http", "https"}
MAX_HOSTNAME_NUMBER = 255
PARTS_IPV4_HOSTNAME = 4
MIN_PARTS_IPV4_HOSTNAME = 2
MAX_ASCII_VALUE = 127


class URLValidator:
    """Validates and normalizes URLs for malware checking."""

    # Constants
    MIN_URL_LENGTH = MIN_URL_LENGTH
    MAX_URL_LENGTH = MAX_URL_LENGTH
    VALID_SCHEMES = VALID_SCHEMES

    @staticmethod
    def validate(url: str) -> str:
        """Validate a URL and return normalized form.

        Args:
            url: The URL to validate (may include scheme and port).

        Returns:
            Normalized URL string.

        Raises:
            ValueError: If URL is invalid with descriptive message.
        """
        if not url:
            msg = "URL cannot be empty"
            raise ValueError(msg)

        if not isinstance(url, str):
            msg = "URL must be a string"
            raise ValueError(msg)

        # Check length
        if len(url) < URLValidator.MIN_URL_LENGTH:
            msg = f"URL too short (minimum {URLValidator.MIN_URL_LENGTH} characters)"
            raise ValueError(msg)

        if len(url) > URLValidator.MAX_URL_LENGTH:
            msg = f"URL exceeds maximum length of {URLValidator.MAX_URL_LENGTH}"
            raise ValueError(msg)

        # Add scheme if missing
        url_to_parse = url
        if not url.startswith(("http://", "https://")):
            # Try to detect if it's just a hostname
            if "://" not in url:
                url_to_parse = f"https://{url}"
            else:
                msg = "URL must use http:// or https:// scheme"
                raise ValueError(msg)

        # Parse URL
        try:
            parsed = urlparse(url_to_parse)
        except Exception as e:
            msg = f"Invalid URL format: {e}"
            raise ValueError(msg) from e

        # Validate scheme
        if parsed.scheme not in URLValidator.VALID_SCHEMES:
            msg = f"Invalid scheme '{parsed.scheme}'. Must be http or https."
            raise ValueError(msg)

        # Validate hostname
        if not parsed.hostname:
            msg = "URL must include a hostname/domain"
            raise ValueError(msg)

        # Validate hostname format (basic check)
        hostname = parsed.hostname.lower()
        if not URLValidator._is_valid_hostname(hostname):
            msg = f"Hostname '{hostname}' is not valid."
            raise ValueError(msg)

        # Reconstruct normalized URL
        return URLValidator._reconstruct_url(parsed)

    @staticmethod
    def _is_valid_hostname(hostname: str) -> bool:
        """Validate hostname format.

        Args:
            hostname: The hostname to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not hostname:
            return False

        # Allow internationalized domain names (IDN)
        # Basic check: not empty, contains at least one dot for TLD or is localhost
        if hostname == "localhost":
            return True

        # Check for valid characters (alphanumeric, hyphens, dots, and non-ASCII for IDN)
        if not all(c.isalnum() or c in ".-:" or ord(c) > MAX_ASCII_VALUE for c in hostname):
            return False

        # Must have at least 2 parts separated by dot (or be localhost/IP)
        parts = hostname.split(".")
        # Return True unless hostname has too few parts and isn't localhost or valid IP
        return not (
            len(parts) < MIN_PARTS_IPV4_HOSTNAME
            and hostname != "localhost"
            and not URLValidator._is_valid_ip(hostname)
        )

    @staticmethod
    def _is_valid_ip(ip_string: str) -> bool:
        """Check if string is valid IPv4 address.

        Args:
            ip_string: The IP string to check.

        Returns:
            True if valid IPv4, False otherwise.
        """
        parts = ip_string.split(".")
        if len(parts) != PARTS_IPV4_HOSTNAME:
            return False

        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > MAX_HOSTNAME_NUMBER:
                    return False
            except ValueError:
                return False

        return True

    @staticmethod
    def _reconstruct_url(parsed: ParseResult) -> str:
        """Reconstruct normalized URL from parsed components.

        Args:
            parsed: ParseResult from urlparse.

        Returns:
            Normalized URL string.
        """
        scheme = parsed.scheme or "https"
        hostname = (parsed.hostname or "").lower()
        port = parsed.port

        # Construct netloc
        netloc = hostname
        if port and not URLValidator._is_default_port(scheme, port):
            netloc = f"{hostname}:{port}"

        # Construct path and query
        path = parsed.path or "/"
        query_string = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""

        # Reconstruct full URL
        return f"{scheme}://{netloc}{path}{query_string}{fragment}"

    @staticmethod
    def _is_default_port(scheme: str, port: int) -> bool:
        """Check if port is default for scheme.

        Args:
            scheme: The URL scheme (http, https).
            port: The port number.

        Returns:
            True if port is default for scheme.
        """
        default_ports = {"http": 80, "https": 443}
        return port == default_ports.get(scheme)

    @staticmethod
    def extract_hostname_and_port(url: str) -> tuple[str, int]:
        """Extract hostname and port from a URL.

        Args:
            url: The URL to parse.

        Returns:
            Tuple of (hostname, port).

        Raises:
            ValueError: If URL is invalid.
        """
        normalized = URLValidator.validate(url)
        parsed = urlparse(normalized)

        hostname = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        return hostname, port

    @staticmethod
    def extract_path(url: str) -> str:
        """Extract path and query from a URL.

        Args:
            url: The URL to parse.

        Returns:
            The path with query string (e.g., "/path?query=value").

        Raises:
            ValueError: If URL is invalid.
        """
        normalized = URLValidator.validate(url)
        parsed = urlparse(normalized)

        path = parsed.path or "/"
        query_string = f"?{parsed.query}" if parsed.query else ""

        return f"{path}{query_string}"
