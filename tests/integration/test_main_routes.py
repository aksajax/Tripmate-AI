
"""Integration tests for main application routes and authentication."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_expected_api_routes_are_registered() -> None:
    """Verify the expected endpoints are present in the OpenAPI schema."""
    paths = set(app.openapi()["paths"])

    expected_paths = {
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/users/me",
        "/api/v1/trips",
        "/api/v1/trips/{trip_id}",
    }

    missing_paths = expected_paths - paths

    assert not missing_paths, f"Missing API routes: {missing_paths}"


def test_health_endpoint_returns_success() -> None:
    """Verify the health endpoint responds successfully."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["app_name"] == "TripMate AI"


def test_user_profile_requires_authentication() -> None:
    """Verify profile access is denied without a bearer token."""
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_registration_rejects_empty_payload() -> None:
    """Verify registration validates its required fields."""
    response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
