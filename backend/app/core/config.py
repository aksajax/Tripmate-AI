
"""Central configuration for TripMate AI."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


# config.py -> core -> app -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Load and validate TripMate AI configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application
    app_name: str = "TripMate AI"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    timezone: str = "Asia/Kolkata"

    # FastAPI backend
    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    backend_base_url: str = "http://127.0.0.1:8000"

    # Keep the raw environment value separate from the parsed property.
    cors_origins_raw: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501",
        validation_alias="CORS_ORIGINS",
    )

    # Streamlit frontend
    frontend_host: str = "127.0.0.1"
    frontend_port: int = Field(default=8501, ge=1, le=65535)
    frontend_base_url: str = "http://127.0.0.1:8501"
    api_request_timeout_seconds: float = Field(default=30, gt=0)

    # PostgreSQL
    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "tripmate_ai"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("CHANGE_ME")
    db_sslmode: str = "disable"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: float = Field(default=30, gt=0)
    db_echo_sql: bool = False

    # LangGraph checkpoint storage
    checkpoint_backend: Literal["postgres"] = "postgres"

    # Local Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_request_timeout_seconds: float = Field(default=120, gt=0)
    ollama_temperature: float = Field(default=0.2, ge=0, le=2)
    ollama_max_retries: int = Field(default=2, ge=0)

    # Travel data providers
    travel_data_mode: Literal["mock", "live", "hybrid"] = "mock"
    flight_provider: str = "mock"
    hotel_provider: str = "mock"
    weather_provider: str = "mock"
    destination_provider: str = "mock"
    currency_provider: str = "mock"

    # Optional provider credentials
    tavily_api_key: SecretStr = SecretStr("")
    amadeus_client_id: SecretStr = SecretStr("")
    amadeus_client_secret: SecretStr = SecretStr("")
    amadeus_base_url: str = "https://test.api.amadeus.com"

    # Trip validation and workflow
    max_trip_days: int = Field(default=30, ge=1)
    max_travelers: int = Field(default=12, ge=1)
    max_workflow_retries: int = Field(default=2, ge=0)
    workflow_timeout_seconds: float = Field(default=300, gt=0)
    require_approval_before_finalization: bool = True

    # Security
    app_secret_key: SecretStr = SecretStr("CHANGE_ME_TO_A_RANDOM_SECRET")
    access_token_expire_minutes: int = Field(default=30, ge=1)

    # Logging and auditing
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    audit_log_enabled: bool = True

    # Feature flags
    enable_live_travel_data: bool = False
    enable_mcp_tools: bool = False
    enable_itinerary_export: bool = True

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins into a clean list."""
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def database_url(self) -> URL:
        """Build a PostgreSQL URL without manually escaping credentials."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": self.db_sslmode},
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for application-wide reuse."""
    return Settings()
