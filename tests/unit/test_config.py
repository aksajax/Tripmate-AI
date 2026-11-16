
"""Unit tests for TripMate AI application configuration."""

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Prevent cached settings from leaking between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_read_environment_variables(monkeypatch):
    """Settings should load values from environment variables."""
    monkeypatch.setenv("APP_NAME", "TripMate Config Test")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("API_V1_PREFIX", "/api/v1")

    settings = get_settings()

    assert settings.app_name == "TripMate Config Test"
    assert settings.app_env == "testing"
    assert settings.debug is False
    assert settings.api_v1_prefix == "/api/v1"


def test_cors_origins_are_parsed(monkeypatch):
    """Comma-separated CORS origins should become a list."""
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501",
    )

    settings = get_settings()

    assert settings.cors_origins == [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]


def test_database_url_uses_configured_values(monkeypatch):
    """The database URL should use the configured PostgreSQL settings."""
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "tripmate_test")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test@password")

    settings = get_settings()
    url = settings.database_url

    assert url.drivername == "postgresql+psycopg"
    assert url.host == "localhost"
    assert url.port == 5433
    assert url.database == "tripmate_test"
    assert url.username == "test_user"
    assert url.password == "test@password"
