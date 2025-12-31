"""Abstract base class for malware database loaders."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class ThreatInfo:
    """Information about a detected threat."""

    is_malicious: bool
    threat_type: str | None = None
    threat_level: str = "safe"  # safe, low, medium, high, critical
    confidence_score: float = 1.0
    metadata: dict | None = None
    detected_by: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        """Validate and normalize threat data."""
        if self.timestamp is None:
            self.timestamp = datetime.now(tz=UTC)

        if self.is_malicious and self.threat_level == "safe":
            self.threat_level = "medium"

        if self.metadata is None:
            self.metadata = {}


class BaseLoader(ABC):
    """Abstract base class for malware database loaders."""

    def __init__(self, name: str, timeout_seconds: float = 5.0):
        """Initialize the loader.

        Args:
            name: Unique identifier for this loader.
            timeout_seconds: Timeout for database queries.
        """
        self.name = name
        self.timeout_seconds = timeout_seconds
        self._ready = False

    async def initialize(self) -> None:
        """Initialize the loader (load files, connect to services, etc).

        Called once at application startup. Override in subclasses.
        """
        self._ready = True

    async def shutdown(self) -> None:
        """Shutdown the loader (cleanup resources).

        Called once at application shutdown. Override in subclasses.
        """
        self._ready = False

    @abstractmethod
    async def lookup(self, hostname: str, port: int = 80, path: str = "/") -> ThreatInfo:
        """Check if a URL is in the malware database.

        Args:
            hostname: The hostname to check.
            port: The port number (default: 80).
            path: The URL path (default: "/").

        Returns:
            ThreatInfo object indicating if URL is malicious.

        Raises:
            TimeoutError: If query exceeds timeout.
            Exception: If database is unavailable.
        """

    def is_ready(self) -> bool:
        """Check if loader is ready to accept queries."""
        return self._ready

    def __repr__(self) -> str:
        """String representation of loader."""
        return f"{self.__class__.__name__}(name={self.name}, ready={self._ready})"
