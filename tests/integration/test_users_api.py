
"""Integration tests for the authenticated user profile endpoint."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.users import router as users_router
from app.main import app


def make_client(user: SimpleNamespace) -> TestClient:
    """Build a client with the current-user dependency overridden."""

    def override_current_user() -> SimpleNamespace:
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    expected_path = "/api/v1/users/me"
    if not any(
        getattr(route, "path", None) == expected_path
        for route in app.routes
    ):
        app.include_router(users_router, prefix="/api/v1")

    return TestClient(app)


def teardown_function() -> None:
    """Clear dependency overrides after each test."""
    app.dependency_overrides.clear()


def test_get_my_profile_returns_public_user_fields() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        password_hash="must-not-be-exposed",
        is_superuser=False,
    )
    client = make_client(user)

    response = client.get("/api/v1/users/me")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert body["display_name"] == user.display_name
    assert body["is_active"] is True
    assert "password_hash" not in body
    assert "password" not in body
    assert "is_superuser" not in body


def test_profile_response_contains_creation_timestamp() -> None:
    created_at = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)
    user = SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
        created_at=created_at,
    )
    client = make_client(user)

    response = client.get("/api/v1/users/me")

    assert response.status_code == 200, response.text
    assert response.json()["created_at"] == "2026-01-15T10:30:00Z"


def test_profile_route_is_get_only() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    client = make_client(user)

    response = client.post("/api/v1/users/me")

    assert response.status_code == 405
