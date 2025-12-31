"""Test fixtures and configuration for pytest."""

import asyncio
import importlib
from pathlib import Path

import pytest
from aiohttp import web
from fastapi.testclient import TestClient

import src.main
from src.api import urlinfo as urlinfo_module
from src.main import app as test_app
from src.main import create_malware_checker as create_checker
from src.utils.cache import url_cache


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    yield loop
    loop.close()


@pytest.fixture
def async_client():
    """Create a test client with initialized malware checker."""

    # Reload main module to get fresh app and checker
    importlib.reload(src.main)

    # Initialize malware checker for testing
    test_checker = create_checker()

    # Initialize loaders synchronously in test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_checker.initialize())
    urlinfo_module.set_malware_checker(test_checker)

    # Create and return test client
    client = TestClient(test_app)
    yield client

    # Cleanup
    loop.run_until_complete(test_checker.shutdown())
    loop.close()


@pytest.fixture
def client():
    """Alias for async_client for integration tests."""

    # Reload main module to get fresh app and checker
    importlib.reload(src.main)

    # Initialize malware checker for testing
    test_checker = create_checker()

    # Initialize loaders synchronously in test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_checker.initialize())
    urlinfo_module.set_malware_checker(test_checker)

    # Create and return test client
    test_client = TestClient(test_app)
    yield test_client

    # Cleanup
    loop.run_until_complete(test_checker.shutdown())
    loop.close()


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the URL cache before each test."""
    url_cache.clear()
    yield
    url_cache.clear()


@pytest.fixture
def sample_malware_file(tmp_path: Path) -> Path:
    """Create a temporary malware URL list file for testing."""
    malware_file = tmp_path / "malware_test.csv"
    content = """hostname,port,path
example.com,80,/
evil.net,443,/trojan
bad.org,8080,/malware.exe
"""
    malware_file.write_text(content)
    return malware_file


@pytest.fixture
def sample_clean_file(tmp_path: Path) -> Path:
    """Create a temporary clean URL list file for testing."""
    clean_file = tmp_path / "clean_test.csv"
    content = """hostname,port,path
google.com,80,/
github.com,443,/
python.org,80,/
"""
    clean_file.write_text(content)
    return clean_file


@pytest.fixture
def mock_settings(monkeypatch, tmp_path: Path):
    """Mock settings for testing with temporary database files."""
    monkeypatch.setenv("MALWARE_DB_FILES", str(tmp_path / "malware.csv"))
    monkeypatch.setenv("CACHE_ENABLED", "true")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "3600")


@pytest.fixture
async def mock_http_server():
    """Create a mock HTTP server for testing external database endpoints."""

    async def handle_malware_list(request):
        """Handle requests for malware URL list."""
        return web.json_response(
            {
                "urls": [
                    {"hostname": "malware1.com", "port": 80, "path": "/"},
                    {"hostname": "malware2.net", "port": 443, "path": "/payload"},
                ]
            }
        )

    app = web.Application()
    app.router.add_get("/api/malware-urls", handle_malware_list)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8765)
    await site.start()

    yield "http://127.0.0.1:8765"

    await runner.cleanup()
