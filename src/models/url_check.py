"""Pydantic models for URL validation and API responses."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constants
MIN_URL_LENGTH = 10


class URLCheckRequest(BaseModel):
    """Request model for URL checking endpoint."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"url": "https://malware.example.com:443/trojan"}}
    )

    url: str = Field(
        ...,
        description="The URL to check (scheme://hostname:port/path)",
        examples=["https://example.com:443/path", "http://google.com:80/"],
        min_length=7,
        max_length=2048,
    )


class URLCheckResponse(BaseModel):
    """Response model for URL checking endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://malware.example.com:443/trojan",
                "is_malicious": True,
                "threat_level": "high",
                "threat_type": "malware",
                "confidence_score": 0.95,
                "cached": False,
                "databases_queried": ["local-csv", "online-api"],
                "response_time_ms": 125.3,
                "timestamp": "2024-12-30T12:00:00Z",
            }
        }
    )

    url: str = Field(
        ...,
        description="The normalized URL that was checked",
    )
    is_malicious: bool = Field(
        ...,
        description="True if URL is detected as malicious",
    )
    threat_level: str = Field(
        default="safe",
        description="Threat severity: safe, low, medium, high, critical",
    )
    threat_type: str | None = Field(
        default=None,
        description="Type of threat if malicious (malware, phishing, ransomware, etc)",
    )
    confidence_score: float = Field(
        default=1.0,
        description="Confidence level of detection (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    cached: bool = Field(
        default=False,
        description="Whether result was served from cache",
    )
    databases_queried: list[str] = Field(
        default=[],
        description="List of databases that were queried",
    )
    response_time_ms: float = Field(
        default=0.0,
        description="Time taken to check the URL in milliseconds",
        ge=0.0,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.UTC),
        description="When the check was performed",
    )

    @field_validator("url")
    def validate_url_format(self, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            msg = "URL must start with http:// or https://"
            raise ValueError(msg)
        if len(v) < MIN_URL_LENGTH:
            msg = "URL too short"
            raise ValueError(msg)
        return v
