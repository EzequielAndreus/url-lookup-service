"""Configuration management for the Malware URL Detection API."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    # Database Configuration
    malware_db_files: list[str] = ["data/malware_lists/sample_malware.csv"]
    malware_db_http_urls: list[str] = []

    # Cache Configuration
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    cache_max_entries: int = 10000

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_log_level: str = "INFO"

    # Performance Configuration
    db_query_timeout_seconds: float = 5.0
    connection_pool_size: int = 100
    # API request timeout: maximum time to allow a full request to complete (seconds)
    api_request_timeout_seconds: float = 10.0

    # Feature Flags
    enable_cors: bool = False
    cors_origins: list[str] = ["*"]


# Global settings instance
settings = Settings()
