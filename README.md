# URL Lookup Service

A fast, async-native API service for detecting malicious URLs. Checks provided URLs against multiple malware databases (file-based and HTTP endpoints) and returns comprehensive threat information.

## Features

- **Multi-Database Support**: Query multiple malware databases simultaneously
- **Async/Concurrent**: Built on FastAPI and asyncio for high concurrency
- **Intelligent Caching**: TTL-based in-memory caching reduces response times by 5-10x
- **Graceful Degradation**: Handles partial database failures gracefully
- **Audit Logging**: Comprehensive request/response logging for compliance
- **Request Correlation**: Unique request IDs for tracing through system logs
- **Health Checks**: Built-in health endpoint for monitoring
- **Performance Optimized**: Sub-100ms response times for cached queries, 50-100ms for new queries

## Quick Start

### Prerequisites

- Python 3.11+
- pip or [uv](https://docs.astral.sh/uv/)

### Installation

```bash
# Clone the repository
git clone https://github.com/EzequielAndreus/url-lookup-service.git
cd url-lookup-service

# Install dependencies based on your needs (see Dependency Groups below)
# For local development (recommended):
uv sync --all-groups

# Or install specific groups:
uv sync --group test      # For running tests
uv sync --group dev       # For linting and type checking
uv sync --group commit    # For pre-commit hooks

# Alternative with pip:
pip install -e ".[test]"  # Install with test dependencie

This project uses dependency groups to keep installations lean and purpose-specific:

| Group | Purpose | Dependencies | When to Use |
|-------|---------|--------------|-------------|
| **Main** | Runtime dependencies | FastAPI, Uvicorn, Pydantic, etc. | Always required |
| **test** | Testing framework | pytest, pytest-asyncio, pytest-cov, aiohttp | Running tests |
| **dev** | Code quality tools | ruff, mypy | Linting and type checking |
| **commit** | Git hooks | pre-commit | Running pre-commit hooks |

# Set up environment
cp .env.example .env
```

### Running the Service

```bash
# Development mode with auto-reload
uv run python -m src.main

# Or with uvicorn directly
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

**OpenAPI Docs**: http://localhost:8000/docs

## Testing with Postman

A Postman collection is included in this repository for easy API testing.

### Importing the Collection

1. **Open Postman** (Desktop app or web)
2. Click **Import** button
3. Select the file: `postman/collections/url-lookup-service.postman_collection.json`
4. The collection will appear in your Postman workspace

### Setting Up the Environment

The collection uses a `baseURL` variable that defaults to `http://localhost:8000`. 

### Available Requests

The collection includes the following pre-configured requests:

- **Health**: `GET /health` - Check service health status
- **GitHub**: `GET /urlinfo/1/github.com/` - Example safe URL check
- **Malicious**: `GET /urlinfo/1/evil.net:80/trojan` - Example malicious URL check
- **url_with_port**: `GET /urlinfo/1/example.com:443/path?query=value` - URL with port and query parameters

## API Endpoints

### Check URL for Malware

**Endpoint**: `GET /urlinfo/1/{hostname_and_port}/{original_path_and_query_string}`

Check if a URL is malicious.

**Path Parameters**:
- `hostname_and_port`: Hostname with optional port (e.g., `example.com`, `example.com:8080`)
- `original_path_and_query_string`: URL path and query string (e.g., `path/to/page?query=value`)

**Example Requests**:

```bash
# Safe URL
curl http://localhost:8000/urlinfo/1/github.com/

# URL with port
curl http://localhost:8000/urlinfo/1/example.com:443/path?query=value

# URL with path
curl http://localhost:8000/urlinfo/1/google.com/search
```

**Response** (200 OK):

```json
{
  "url": "https://github.com/",
  "is_malicious": false,
  "threat_level": "safe",
  "threat_type": null,
  "confidence_score": 0.0,
  "cached": false,
  "databases_queried": ["file-db1.csv", "http-endpoint-0"],
  "response_time_ms": 78.42
}
```

### Health Check

**Endpoint**: `GET /health`

Check service health status.

**Response** (200 OK):

```json
{
  "status": "healthy",
  "service": "malware-url-detection",
  "loader_status": {
    "file-db1.csv": {
      "status": "ready",
      "urls_loaded": 10000
    },
    "http-endpoint-0": {
      "status": "ready"
    }
  }
}
```

**Possible Status Values**:
- `healthy`: All database loaders ready and responding
- `degraded`: At least one loader is unavailable, but service continues
- `not_initialized`: Service still starting up

## Configuration

Configuration is managed through environment variables. See `.env.example` for all available options.

**Key Settings**:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_LOG_LEVEL=INFO

# Database Configuration
MALWARE_DB_FILES=data/malware_urls.csv
MALWARE_DB_HTTP_URLS=http://api.example.com/malware-check

# Cache Configuration
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=10000

# Timeouts
DB_QUERY_TIMEOUT_SECONDS=5
```

See `src/config.py` for all available configuration options.

## Performance

### Response Time Baselines

| Scenario | Target | Typical | Notes |
|----------|--------|---------|-------|
| Single request (new) | < 1000ms | 50-100ms | Multiple databases queried in parallel |
| Cached response | < 10ms | 1-5ms | Cache hit significantly faster |
| Validation error | < 100ms | 10-30ms | Fast rejection of invalid URLs |
| Concurrent requests | 10+ | 20+ req/sec | Async handling |

### Optimization Tips

**1. Cache Configuration**
- `CACHE_TTL_SECONDS`: Longer TTL = fewer database queries (default: 3600s)
- `CACHE_MAX_SIZE`: Larger cache = better hit rate (default: 10000 entries)

**2. Timeout Tuning**
- `DB_QUERY_TIMEOUT_SECONDS`: Balance between reliability and latency (default: 5s)
- Faster timeouts reduce worst-case latency but increase failure risk

**3. Database Loading**
- File-based databases: Loaded once at startup, very fast lookups
- HTTP endpoints: Network calls, add ~50-100ms, consider increasing timeout

**4. Concurrency**
- Uses asyncio for concurrent database queries
- All databases queried in parallel (gathering), not sequentially
- Single event loop handles many concurrent connections

### Load Testing

Test with Apache Bench or similar:

```bash
# 1000 requests with 100 concurrent connections
ab -n 1000 -c 100 http://localhost:8000/urlinfo/1/example.com/

# With HTTP/2 support
h2load -n 1000 -c 100 http://localhost:8000/urlinfo/1/example.com/
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/contract/test_urlinfo_contract.py

# Run with verbose output
uv run pytest -v
```

### Test Structure

- **Contract Tests** (`tests/contract/`): API specification compliance
- **Integration Tests** (`tests/integration/`): End-to-end workflows
- **Unit Tests** (`tests/unit/`): Individual components

### Test Coverage

Current coverage: **74%** across all modules.

Target coverage: **75%+** (measured with pytest-cov)

## Logging

The service uses structured JSON logging for easy parsing and analysis.

**Log Levels**:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for unexpected but handled conditions
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical system failures

**Request Correlation**:
- Every request gets a unique `X-Request-ID` header
- All logs include the request ID for tracing
- Responses echo the request ID for client reference

Example logs:

```json
{
  "timestamp": "2024-12-30T10:15:30.123456",
  "level": "INFO",
  "service": "malware-url-detection",
  "request_id": "req-uuid-1234",
  "message": "URL check completed",
  "url": "github.com",
  "result": "safe",
  "response_time_ms": 45.23,
  "cached": false
}
```

## Error Handling

The API returns structured error responses with detailed information:

**Invalid URL** (400):

```json
{
  "error": "Invalid hostname",
  "detail": "Invalid hostname",
  "request_id": "req-uuid-1234",
  "type": "http_error"
}
```

**Service Unavailable** (503):

```json
{
  "error": "Malware checker not initialized",
  "detail": "Malware checker not initialized",
  "request_id": "req-uuid-1234",
  "type": "http_error"
}
```

**Internal Error** (500):

```json
{
  "error": "Internal server error",
  "detail": "An unexpected error occurred",
  "request_id": "req-uuid-1234",
  "type": "internal_error"
}
```

## Architecture

### Components

**API Layer** (`src/api/urlinfo.py`)
- FastAPI routes for URL checking
- Request validation
- Response formatting

**Service Layer** (`src/services/`)
- `MalwareChecker`: Orchestrates multi-database queries
- `URLValidator`: Validates URL format
- Database Loaders: Queries specific database sources

**Models** (`src/models/`)
- `URLCheckRequest/Response`: API data models
- `ThreatInfo`: Database threat information

**Infrastructure** (`src/utils/`)
- Caching: TTL-based in-memory cache
- Logging: Structured JSON logging
- Configuration: Environment-based settings

### Data Flow

```
Request
  ↓
[Request ID Middleware] - Add correlation ID
  ↓
[URL Validation] - Validate format
  ↓
[Cache Check] - Check if cached
  ↓ (Cache Hit)
Return Cached Result
  ↓ (Cache Miss)
[Parallel DB Queries] - Query all loaders concurrently
  ↓
[Result Aggregation] - Combine results
  ↓
[Cache Store] - Cache result with TTL
  ↓
[Response Formatting] - Add metadata
  ↓
Response
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy source
COPY src/ src/
COPY data/ data/

# Run
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

For production, set:

```bash
export API_LOG_LEVEL=WARNING
export CACHE_TTL_SECONDS=7200
export DB_QUERY_TIMEOUT_SECONDS=3
```

## Contributing

1. Create a feature branch
2. Add tests (contract-first approach)
3. Implement functionality
4. Ensure all tests pass
5. Submit pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
1. Check [GitHub Issues](https://github.com/EzequielAndreus/url-lookup-service/issues)
2. Review [API Documentation](http://localhost:8000/docs) (when running)
3. Check logs with request ID for debugging

## Roadmap

- [ ] Dashboard for monitoring metrics
- [ ] Database failover strategies
- [ ] URL categorization (phishing, malware, spam)
- [ ] User authentication and API keys
