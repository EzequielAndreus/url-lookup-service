"""HTTP endpoint-based malware database loader."""

import httpx

from src.services.database_loaders.base import BaseLoader, ThreatInfo
from src.utils.logging import get_logger

# Constants
SERVER_ERROR_CODE = 500
SUCCESS_CODE = 200

logger = get_logger(__name__)


class HTTPLoader(BaseLoader):
    """Query remote HTTP endpoints for malware URL information."""

    def __init__(
        self,
        name: str,
        endpoint_url: str,
        method: str = "GET",
        timeout_seconds: float = 5.0,
        headers: dict[str, str] | None = None,
    ):
        """Initialize HTTP loader.

        Args:
            name: Unique identifier for this loader.
            endpoint_url: HTTP endpoint URL to query.
            method: HTTP method (GET or POST).
            timeout_seconds: Request timeout.
            headers: Additional HTTP headers.
        """
        super().__init__(name, timeout_seconds)
        self.endpoint_url = endpoint_url
        self.method = method.upper()
        self.headers = headers or {}
        self.client: httpx.AsyncClient | None = None

        if self.method not in ("GET", "POST"):
            msg = f"Unsupported HTTP method: {method}"
            raise ValueError(msg)

    async def initialize(self) -> None:
        """Initialize HTTP client and test connectivity."""
        self.client = httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers=self.headers,
        )

        # Test connectivity
        try:
            response = await self.client.head(self.endpoint_url, timeout=self.timeout_seconds)
            if response.status_code < SERVER_ERROR_CODE:
                logger.info(f"HTTP loader {self.name} initialized: {self.endpoint_url}")
                self._ready = True
            else:
                logger.warning(f"HTTP loader {self.name} returned status {response.status_code}")
                self._ready = True
        except Exception as e:
            logger.warning(f"HTTP loader {self.name} connectivity check failed: {e}")
            # Still mark as ready; may be temporarily unavailable
            self._ready = True

    async def shutdown(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
        self._ready = False

    async def lookup(self, hostname: str, port: int = 80, path: str = "/") -> ThreatInfo:
        """Query remote HTTP endpoint for URL status.

        Args:
            hostname: The hostname to check.
            port: The port number.
            path: The URL path.

        Returns:
            ThreatInfo with is_malicious status from endpoint.
        """
        if not self._ready or not self.client:
            return ThreatInfo(
                is_malicious=False,
                detected_by=self.name,
                metadata={"error": "Loader not ready"},
            )

        try:
            # Build query URL
            query_params = {
                "hostname": hostname,
                "port": port,
                "path": path,
            }

            if self.method == "GET":
                response = await self.client.get(
                    self.endpoint_url,
                    params=query_params,
                    timeout=self.timeout_seconds,
                )
            else:  # POST
                response = await self.client.post(
                    self.endpoint_url,
                    json=query_params,
                    timeout=self.timeout_seconds,
                )

            if response.status_code == SUCCESS_CODE:
                data = response.json()
                return self._parse_response(data)

            logger.warning(f"HTTP loader {self.name} returned status {response.status_code}")
            return ThreatInfo(
                is_malicious=False,
                detected_by=self.name,
                metadata={"http_status": response.status_code},
            )

        except httpx.TimeoutException:
            logger.error(f"HTTP loader {self.name} timeout")
            return ThreatInfo(
                is_malicious=False,
                detected_by=self.name,
                metadata={"error": "timeout"},
            )
        except Exception as e:
            logger.error(f"HTTP loader {self.name} query failed: {e}")
            return ThreatInfo(
                is_malicious=False,
                detected_by=self.name,
                metadata={"error": str(e)},
            )

    def _parse_response(self, data: dict) -> ThreatInfo:
        """Parse HTTP response into ThreatInfo.

        Args:
            data: JSON response from endpoint.

        Returns:
            ThreatInfo object.
        """
        # Support multiple response formats
        is_malicious = data.get(
            "is_malicious",
            data.get("malicious", data.get("threat_detected", False)),
        )
        threat_type = data.get("threat_type", data.get("type"))
        threat_level = data.get(
            "threat_level", data.get("level", "safe" if not is_malicious else "medium")
        )
        confidence = data.get(
            "confidence_score", data.get("confidence", 1.0 if is_malicious else 0.0)
        )

        return ThreatInfo(
            is_malicious=is_malicious,
            threat_type=threat_type,
            threat_level=threat_level,
            confidence_score=float(confidence),
            detected_by=self.name,
            metadata=data.get("metadata", {}),
        )
