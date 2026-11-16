
"""Integration tests for TripMate AI authentication endpoints."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service, router as auth_router
from app.db.session import get_db
from app.main import app
from app.services.auth_service import AuthService


def make_user() -> SimpleNamespace:
    """Create a lightweight user object for API tests."""
    return SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def make_client(service: Mock) -> TestClient:
    """Build a client with authentication dependencies overridden."""

    def override_auth_service() -> Mock:
        return service

    def override_db():
        yield None

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_db] = override_db

    # Register the router only if it is not already mounted.
    expected_path = "/api/v1/auth/register"
    if not any(
        getattr(route, "path", None) == expected_path
        for route in app.routes
    ):
        app.include_router(auth_router, prefix="/api/v1")

    return TestClient(app)


def teardown_function() -> None:
    """Clear overrides after every test."""
    app.dependency_overrides.clear()


def test_register_returns_created_user() -> None:
    service = Mock(spec=AuthService)
    service.register.return_value = make_user()
    client = make_client(service)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "traveler@example.com",
            "display_name": "Test Traveler",
            "password": "Strong-Test-Password-123",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["email"] == "traveler@example.com"
    assert "password" not in response.json()
    service.register.assert_called_once()


def test_register_duplicate_email_returns_conflict() -> None:
    service = Mock(spec=AuthService)
    service.register.side_effect = ValueError(
        "A user with this email address already exists"
    )
    client = make_client(service)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "traveler@example.com",
            "display_name": "Test Traveler",
            "password": "Strong-Test-Password-123",
        },
    )

    assert response.status_code == 409, response.text


def test_login_returns_access_token() -> None:
    service = Mock(spec=AuthService)
    service.authenticate.return_value = make_user()
    client = make_client(service)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "traveler@example.com",
            "password": "Strong-Test-Password-123",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_rejects_invalid_credentials() -> None:
    service = Mock(spec=AuthService)
    service.authenticate.return_value = None
    client = make_client(service)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "traveler@example.com",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Invalid email or password"


def test_register_rejects_invalid_payload() -> None:
    service = Mock(spec=AuthService)
    client = make_client(service)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "display_name": "Test Traveler",
            "password": "short",
        },
    )

    assert response.status_code == 422, response.text
    service.register.assert_not_called()
