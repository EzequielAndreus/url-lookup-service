"""Structured logging utilities with request ID correlation."""

import logging
import uuid
from contextvars import ContextVar

from src.config import settings

# Context variable for request ID correlation
request_id_context: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Add request ID to all log records for correlation."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID from context to log record."""
        request_id = request_id_context.get()
        record.request_id = request_id or "no-request-id"
        return True


def setup_logging() -> None:
    """Configure structured logging with request ID correlation."""
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.api_log_level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, settings.api_log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add formatter and filter to handler
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    # Add handler to logger
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with structured logging support."""
    return logging.getLogger(name)


def generate_request_id() -> str:
    """Generate a unique request ID for correlation."""
    return f"req-{uuid.uuid4().hex[:12]}"


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_context.set(request_id)


def get_request_id() -> str:
    """Get the request ID from the current context."""
    return request_id_context.get()


def log_url_lookup(
    url: str,
    is_malicious: bool,
    databases_queried: list[str],
    response_time_ms: float,
    cached: bool = False,
) -> None:
    """Log a URL lookup operation with full context."""
    logger = get_logger(__name__)
    logger.info(
        f"URL lookup: url={url}, is_malicious={is_malicious}, "
        f"databases={databases_queried}, response_time_ms={response_time_ms:.2f}, cached={cached}"
    )


def log_validation_error(url: str, error_detail: str) -> None:
    """Log a validation error with context."""
    logger = get_logger(__name__)
    logger.warning(f"URL validation failed: url={url}, error={error_detail}")


def log_database_error(database_name: str, error_detail: str, response_time_ms: float) -> None:
    """Log a database query error with context."""
    logger = get_logger(__name__)
    logger.warning(
        f"Database query failed: database={database_name}, "
        f"error={error_detail}, response_time_ms={response_time_ms:.2f}"
    )
