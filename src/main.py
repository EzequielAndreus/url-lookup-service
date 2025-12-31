"""FastAPI application initialization for the Malware URL Detection API."""

import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api import urlinfo
from src.config import settings
from src.services.database_loaders.file_loader import FileLoader
from src.services.database_loaders.http_loader import HTTPLoader
from src.services.malware_checker import MalwareChecker
from src.utils import metrics
from src.utils.logging import generate_request_id, get_logger, set_request_id, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global malware checker instance
malware_checker: MalwareChecker | None = None


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to track request processing time and add response timing header."""

    async def dispatch(self, request: Request, call_next):
        """Track request duration and add X-Response-Time header."""
        metrics.incr("requests_total")
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000.0
        response.headers["X-Response-Time"] = f"{process_time:.2f}"
        metrics.timing("response_time_ms", process_time)
        metrics.incr("responses_total")
        logger.debug(f"{request.method} {request.url.path} completed in {process_time:.2f}ms")
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to catch and log unhandled exceptions."""

    async def dispatch(self, request: Request, call_next):
        """Catch exceptions and return structured error responses."""
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = request.headers.get("X-Request-ID", "unknown")
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}: {exc}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred",
                    "request_id": request_id,
                    "type": "internal_error",
                },
            )


def create_malware_checker() -> MalwareChecker:
    """Create and initialize the malware checker with configured loaders."""
    loaders = []

    # Add file-based loaders
    for file_path in settings.malware_db_files:
        loader = FileLoader(
            name=f"file-{file_path.split('/')[-1]}",
            file_path=file_path,
            file_format="csv",
            timeout_seconds=settings.db_query_timeout_seconds,
        )
        loaders.append(loader)
        logger.info(f"Configured file loader: {loader.name} -> {file_path}")

    # Add HTTP-based loaders
    for idx, http_url in enumerate(settings.malware_db_http_urls):
        loader = HTTPLoader(
            name=f"http-endpoint-{idx}",
            endpoint_url=http_url,
            method="GET",
            timeout_seconds=settings.db_query_timeout_seconds,
        )
        loaders.append(loader)
        logger.info(f"Configured HTTP loader: {loader.name} -> {http_url}")

    checker = MalwareChecker(loaders, cache_enabled=settings.cache_enabled)
    logger.info(f"Created malware checker with {len(loaders)} loaders")
    return checker


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifecycle (startup and shutdown)."""

    # Startup
    logger.info("Starting Malware URL Detection API")
    logger.info(
        f"Configuration: host={settings.api_host}, port={settings.api_port}, "
        f"cache_enabled={settings.cache_enabled}, cache_ttl={settings.cache_ttl_seconds}s"
    )

    # Initialize malware checker
    malware_checker = create_malware_checker()
    await malware_checker.initialize()
    app.state.malware_checker = malware_checker
    urlinfo.set_malware_checker(malware_checker)

    logger.info(f"Malware checker ready: {malware_checker.get_status()}")

    yield

    # Shutdown
    logger.info("Shutting down Malware URL Detection API")
    if malware_checker:
        await malware_checker.shutdown()


# Initialize FastAPI application
app = FastAPI(
    title="Malware URL Detection API",
    description="Fast, async-native service for detecting malicious URLs",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (configure as needed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestTimeoutMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for correlation."""
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    if hasattr(request.app.state, "malware_checker"):
        return request.app.state.malware_checker.get_status()
    return {"status": "not_ready", "service": "malware-url-detection"}


app.include_router(urlinfo.router)


@app.get("/metrics")
async def metrics_endpoint():
    """Return runtime metrics as JSON."""
    return metrics.get_metrics()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with request context."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.warning(
        f"HTTP {exc.status_code} error for {request.method} {request.url.path}: {exc.detail}",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "detail": exc.detail,
            "request_id": request_id,
            "type": "http_error",
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(
        f"Unhandled exception for {request.method} {request.url.path}: {exc}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "request_id": request_id,
            "type": "internal_error",
        },
        headers={"X-Request-ID": request_id},
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.api_log_level.lower(),
    )
