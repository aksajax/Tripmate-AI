
"""Integration tests for authenticated TripMate AI trip endpoints."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.trips import get_trip_service, router as trips_router
from app.main import app
from app.services.trip_service import TripService
from app.repositories.trip_repository import TripRepository


def make_user() -> SimpleNamespace:
    """Create a lightweight authenticated user."""
    return SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
    )


def make_trip(user_id, **overrides) -> SimpleNamespace:
    """Create a lightweight trip matching the response schema."""
    values = {
        "id": uuid4(),
        "user_id": user_id,
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": date(2027, 1, 10),
        "end_date": date(2027, 1, 15),
        "travelers": 2,
        "budget": Decimal("25000.00"),
        "currency": "INR",
        "travel_style": "balanced",
        "special_requirements": None,
        "status": "draft",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)




def make_client(user: SimpleNamespace, service: Mock) -> TestClient:
    """Build a test client with authentication and service overrides."""

    def override_current_user():
        return user

    def override_trip_service():
        return service

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_trip_service] = override_trip_service

    return TestClient(app)




def teardown_function() -> None:
    """Clear dependency overrides after every test."""
    app.dependency_overrides.clear()


def test_create_trip_uses_authenticated_user() -> None:
    user = make_user()
    service = Mock(spec=TripService)
    service.create_trip.return_value = make_trip(user.id)
    client = make_client(user, service)

    response = client.post(
        "/api/v1/trips",
        json={
            "origin": "Bengaluru",
            "destination": "Goa",
            "start_date": "2027-01-10",
            "end_date": "2027-01-15",
            "travelers": 2,
            "budget": "25000.00",
            "currency": "INR",
            "travel_style": "balanced",
        },
    )

    assert response.status_code == 201, response.text
    service.create_trip.assert_called_once()
    assert service.create_trip.call_args.kwargs["user_id"] == user.id



def test_get_trip_returns_owned_trip(monkeypatch) -> None:
    user = make_user()
    trip = make_trip(user.id)

    repository = Mock(spec=TripRepository)
    repository.get_by_id_for_user.return_value = trip
    monkeypatch.setattr(
        TripRepository,
        "get_by_id_for_user",
        repository.get_by_id_for_user,
    )

    client = make_client(user, Mock(spec=TripService))
    response = client.get(f"/api/v1/trips/{trip.id}")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(trip.id)
    repository.get_by_id_for_user.assert_called_once_with(
        trip_id=trip.id,
        user_id=user.id,
    )


def test_get_trip_hides_another_users_trip(monkeypatch) -> None:
    user = make_user()

    repository = Mock(spec=TripRepository)
    repository.get_by_id_for_user.return_value = None
    monkeypatch.setattr(
        TripRepository,
        "get_by_id_for_user",
        repository.get_by_id_for_user,
    )

    client = make_client(user, Mock(spec=TripService))
    response = client.get(f"/api/v1/trips/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"


def test_get_missing_trip_returns_404(monkeypatch) -> None:
    user = make_user()

    repository = Mock(spec=TripRepository)
    repository.get_by_id_for_user.return_value = None
    monkeypatch.setattr(
        TripRepository,
        "get_by_id_for_user",
        repository.get_by_id_for_user,
    )

    client = make_client(user, Mock(spec=TripService))
    response = client.get(f"/api/v1/trips/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"



def test_list_trips_only_requests_authenticated_users_trips() -> None:
    user = make_user()
    service = Mock(spec=TripService)
    service.list_user_trips.return_value = [make_trip(user.id)]
    client = make_client(user, service)

    response = client.get("/api/v1/trips?limit=10&offset=0")

    assert response.status_code == 200, response.text
    service.list_user_trips.assert_called_once_with(
        user_id=user.id,
        limit=10,
        offset=0,
    )


def test_list_trips_rejects_invalid_limit() -> None:
    user = make_user()
    service = Mock(spec=TripService)
    client = make_client(user, service)

    response = client.get("/api/v1/trips?limit=0")

    assert response.status_code == 422
    service.list_user_trips.assert_not_called()


def test_list_trips_passes_pagination_parameters() -> None:
    """Return the authenticated user's trips with requested pagination."""
    user = make_user()
    trip = make_trip(user.id)

    service = Mock(spec=TripService)
    service.list_user_trips.return_value = [trip]
    client = make_client(user, service)

    response = client.get("/api/v1/trips?limit=10&offset=5")

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(trip.id)

    service.list_user_trips.assert_called_once_with(
        user_id=user.id,
        limit=10,
        offset=5,
    )


def test_list_trips_returns_empty_list_when_user_has_no_trips() -> None:
    """Return an empty list when the user has no trips."""
    user = make_user()

    service = Mock(spec=TripService)
    service.list_user_trips.return_value = []
    client = make_client(user, service)

    response = client.get("/api/v1/trips")

    assert response.status_code == 200, response.text
    assert response.json() == []

    service.list_user_trips.assert_called_once_with(
        user_id=user.id,
        limit=20,
        offset=0,
    )
