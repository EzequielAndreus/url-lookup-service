"""File-based malware database loader (CSV/JSON)."""

import asyncio
import csv
import json
from pathlib import Path

import aiofiles

from src.services.database_loaders.base import BaseLoader, ThreatInfo
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FileLoader(BaseLoader):
    """Load malware URLs from CSV or JSON files."""

    def __init__(
        self,
        name: str,
        file_path: str,
        file_format: str = "csv",
        timeout_seconds: float = 5.0,
    ):
        """Initialize file loader.

        Args:
            name: Unique identifier for this loader.
            file_path: Path to CSV or JSON file containing malware URLs.
            file_format: "csv" or "json".
            timeout_seconds: Timeout for file operations.
        """
        super().__init__(name, timeout_seconds)
        self.file_path = Path(file_path)
        self.file_format = file_format.lower()
        self.malware_urls: set[tuple[str, int, str]] = set()

        if self.file_format not in ("csv", "json"):
            msg = f"Unsupported format: {self.file_format}"
            raise ValueError(msg)

    async def initialize(self) -> None:
        """Load malware URLs from file into memory."""
        if not self.file_path.exists():
            logger.warning(f"Malware file not found: {self.file_path}")
            self._ready = True
            return

        try:
            if self.file_format == "csv":
                await self._load_csv()
            else:
                await self._load_json()

            logger.info(
                f"Loaded {len(self.malware_urls)} URLs from {self.file_path} "
                f"({self.file_format.upper()})"
            )
            self._ready = True
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            raise

    async def _load_csv(self) -> None:
        """Load malware URLs from CSV file."""
        async with aiofiles.open(self.file_path) as f:
            content = await f.read()

        # Parse CSV in executor to avoid blocking
        loop = asyncio.get_event_loop()
        self.malware_urls = await loop.run_in_executor(None, self._parse_csv, content)

    def _parse_csv(self, content: str) -> set[tuple[str, int, str]]:
        """Parse CSV content (runs in executor)."""
        urls = set()
        reader = csv.DictReader(content.splitlines())

        for row in reader:
            if not row:
                continue

            hostname = row.get("hostname", "").strip().lower()
            try:
                port = int(row.get("port", "80"))
            except (ValueError, TypeError):
                port = 80

            path = row.get("path", "/").strip() or "/"

            if hostname:
                urls.add((hostname, port, path))

        return urls

    async def _load_json(self) -> None:
        """Load malware URLs from JSON file."""
        async with aiofiles.open(self.file_path) as f:
            content = await f.read()

        data = json.loads(content)

        # Handle different JSON structures
        if isinstance(data, list):
            urls = data
        elif isinstance(data, dict):
            # Try common keys
            urls = (
                data.get("urls")
                or data.get("malware_urls")
                or data.get("entries")
                or data.get("data")
                or []
            )
        else:
            urls = []

        for entry in urls:
            if not isinstance(entry, dict):
                continue

            hostname = entry.get("hostname", "").strip().lower()
            try:
                port = int(entry.get("port", "80"))
            except (ValueError, TypeError):
                port = 80

            path = entry.get("path", "/").strip() or "/"

            if hostname:
                self.malware_urls.add((hostname, port, path))

    async def lookup(self, hostname: str, port: int = 80, path: str = "/") -> ThreatInfo:
        """Check if URL is in the malware database.

        Args:
            hostname: The hostname to check.
            port: The port number.
            path: The URL path.

        Returns:
            ThreatInfo with is_malicious status.
        """
        if not self._ready:
            return ThreatInfo(
                is_malicious=False,
                threat_type=None,
                detected_by=self.name,
                metadata={"error": "Loader not ready"},
            )

        # Normalize inputs
        hostname_normalized = hostname.lower().strip()
        path_normalized = path.strip() or "/"

        # Check exact match
        exact_match = (hostname_normalized, port, path_normalized) in self.malware_urls

        # Check hostname+port with any path (more lenient matching)
        hostname_port_match = any(
            h == hostname_normalized and p == port for h, p, _ in self.malware_urls
        )

        is_malicious = exact_match or hostname_port_match

        return ThreatInfo(
            is_malicious=is_malicious,
            threat_type="malware" if is_malicious else None,
            threat_level="high" if is_malicious else "safe",
            confidence_score=1.0 if is_malicious else 0.0,
            detected_by=self.name,
            metadata={"database_size": len(self.malware_urls)},
        )

    def get_database_size(self) -> int:
        """Get number of URLs in database."""
        return len(self.malware_urls)
