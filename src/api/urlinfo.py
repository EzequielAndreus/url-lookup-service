"""FastAPI router for URL lookup endpoints."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.config import settings
from src.models.url_check import URLCheckResponse
from src.services.malware_checker import MalwareChecker
from src.utils.logging import get_logger

# Constants
HTTPS_PORT = 443
MIN_LEN_HOSTNAME = 2
MAX_URL_LENGTH = 2048

logger = get_logger(__name__)

# Create router (will be mounted in main.py)
router = APIRouter(prefix="/urlinfo", tags=["urlinfo"])


# Dependency injection using a simple container class
class MalwareCheckerContainer:
    _instance: MalwareChecker | None = None

    @classmethod
    def set(cls, checker: MalwareChecker) -> None:
        """Set the malware checker instance (called by main.py)."""
        cls._instance = checker

    @classmethod
    def get(cls) -> MalwareChecker:
        """Get the malware checker instance."""
        if cls._instance is None:
            raise HTTPException(
                status_code=503,
                detail="Malware checker not initialized",
            )
        return cls._instance


def set_malware_checker(checker: MalwareChecker) -> None:
    """Set the malware checker instance (called by main.py)."""
    MalwareCheckerContainer.set(checker)


def get_malware_checker() -> MalwareChecker:
    """Dependency injection function to get the malware checker."""
    return MalwareCheckerContainer.get()


@router.get("/1/{hostname_and_port}/{original_path_and_query_string:path}")
async def lookup_url(
    hostname_and_port: str,
    original_path_and_query_string: str = "",
    checker: Annotated[MalwareChecker, Depends(get_malware_checker)] = None,
) -> URLCheckResponse:
    """Check if a URL is malicious.

    Path parameters:
    - hostname_and_port: The hostname and port (e.g., "example.com:80")
    - original_path_and_query_string: The path and query string (e.g., "/path?query=value")

    Returns:
        JSON response with URL safety information and metadata.
    """
    if checker is None:
        checker = get_malware_checker()

    if not checker.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Malware checker not ready",
        )

    # Check total URL length early - use default port/scheme for estimation
    # Parse port first to get proper scheme
    port = 80
    hostname = hostname_and_port

    if ":" in hostname_and_port:
        parts = hostname_and_port.rsplit(":", 1)
        hostname = parts[0]
        try:
            port = int(parts[1])
        except (ValueError, IndexError):
            # Invalid port, will be caught below
            pass

    # Determine scheme based on port
    scheme = "https" if port == HTTPS_PORT else "http"

    normalized_path = (
        f"/{original_path_and_query_string}" if original_path_and_query_string else "/"
    )
    tentative_url = f"{scheme}://{hostname}:{port}{normalized_path}"

    if len(tentative_url) > MAX_URL_LENGTH:
        raise HTTPException(
            status_code=414,
            detail=f"URL exceeds maximum length of {MAX_URL_LENGTH} characters",
        )

    # Validate the port number parsing didn't fail
    if ":" in hostname_and_port:
        parts = hostname_and_port.rsplit(":", 1)
        hostname = parts[0]
        try:
            port = int(parts[1])
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail="Invalid port number in hostname:port",
            ) from None
    else:
        hostname = hostname_and_port
        port = 80

    # Validate hostname
    if not hostname or len(hostname) < MIN_LEN_HOSTNAME:
        raise HTTPException(
            status_code=400,
            detail="Invalid hostname",
        )

    # Normalize path
    path = f"/{original_path_and_query_string}" if original_path_and_query_string else "/"

    try:
        # Check if URL is malicious with API-level timeout
        timeout = settings.api_request_timeout_seconds
        coro = checker.check_url(hostname, port, path)
        is_malicious, databases_queried, result_details = await asyncio.wait_for(
            coro, timeout=timeout
        )

        # Construct full URL for response - determine scheme based on port
        response_scheme = "https" if port == HTTPS_PORT else "http"
        full_url = f"{response_scheme}://{hostname}:{port}{path}"

        return URLCheckResponse(
            url=full_url,
            is_malicious=is_malicious,
            threat_level=result_details.get("threat_level", "safe"),
            threat_type=result_details.get("threat_type"),
            confidence_score=result_details.get("confidence_score", 1.0 if is_malicious else 0.0),
            cached=result_details.get("cached", False),
            databases_queried=databases_queried,
            response_time_ms=result_details.get("response_time_ms", 0.0),
        )

    except TimeoutError:
        logger.warning(f"URL check timed out for {hostname}:{port}{path} after {timeout}s")
        raise HTTPException(
            status_code=503,
            detail=f"URL check timed out after {timeout} seconds",
        ) from None
    except Exception as e:
        logger.error(f"Error checking URL {hostname}:{port}{path}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check URL",
        ) from e


@router.get("/health")
async def health_check(
    checker: Annotated[MalwareChecker, Depends(get_malware_checker)] = None,
) -> dict:
    """Check health of URL lookup service.

    Returns:
        dict: Service health status with loader information
        - status: "healthy", "degraded", or "not_initialized"
        - service: Service name
        - loader_status: Status of all loaders
        - timestamp: Current timestamp
    """

    if checker is None:
        checker = get_malware_checker()

    if not checker:
        return {
            "status": "not_initialized",
            "service": "urlinfo",
            "message": "Malware checker not yet initialized",
        }

    is_ready = checker.is_ready()
    loader_status = checker.get_status()

    return {
        "status": "healthy" if is_ready else "degraded",
        "service": "urlinfo",
        "message": "All database loaders ready"
        if is_ready
        else "Some database loaders are unavailable",
        "loader_status": loader_status,
    }


@router.get("/1/{rest_of_path:path}")
async def catch_invalid_url_paths(rest_of_path: str) -> URLCheckResponse:
    """Catch all requests to /1/* and validate path structure.

    This catches requests that don't match the hostname:port/path pattern.
    """
    if not rest_of_path or rest_of_path.startswith("/"):
        # Empty hostname or malformed path
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format: hostname required",
        )

    # Try to parse as hostname_and_port/path
    parts = rest_of_path.split("/", 1)
    hostname_and_port = parts[0]
    original_path_and_query_string = parts[1] if len(parts) > 1 else ""

    # Validate hostname
    if not hostname_and_port:
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format: hostname required",
        )

    # Delegate to main handler
    return await lookup_url(hostname_and_port, original_path_and_query_string)
