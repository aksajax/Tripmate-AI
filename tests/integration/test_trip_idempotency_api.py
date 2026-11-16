"""Integration tests for idempotent trip creation API behavior."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.trips import (
    get_idempotency_execution_service,
    get_trip_service,
)
from app.main import app
from app.services.idempotency_execution_service import (
    IdempotencyConflictError,
)
from app.services.trip_service import TripService


def make_user():
    """Build an authenticated test user."""
    return SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
    )


def make_trip(user_id):
    """Build a valid trip response object."""
    now = datetime.now(timezone.utc)

    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        origin="Bengaluru",
        destination="Goa",
        start_date=date(2027, 1, 10),
        end_date=date(2027, 1, 15),
        travelers=2,
        budget=Decimal("25000.00"),
        currency="INR",
        travel_style="balanced",
        special_requirements=None,
        status="draft",
        created_at=now,
        updated_at=now,
    )


def make_payload():
    """Return a valid trip creation payload."""
    return {
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": "2027-01-10",
        "end_date": "2027-01-15",
        "travelers": 2,
        "budget": "25000.00",
        "currency": "INR",
        "travel_style": "balanced",
        "special_requirements": None,
    }


def test_first_idempotent_request_creates_and_stores_response():
    """The first request creates a trip and persists its response."""
    user = make_user()
    trip = make_trip(user.id)

    trip_service = Mock(spec=TripService)
    trip_service.create_trip.return_value = trip

    idempotency_service = Mock()
    idempotency_service.find_existing.return_value = None
    idempotency_service.store_response.return_value = (
        SimpleNamespace(
            response_status=201,
            response_body={
                "id": str(trip.id),
                "origin": "Bengaluru",
                "destination": "Goa",
                "start_date": "2027-01-10",
                "end_date": "2027-01-15",
                "travelers": 2,
                "budget": "25000.00",
                "currency": "INR",
                "travel_style": "balanced",
                "special_requirements": None,
                "status": "draft",
                "created_at": trip.created_at.isoformat(),
                "updated_at": trip.updated_at.isoformat(),
            },
        ),
        True,
    )

    db = Mock()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_trip_service] = lambda: trip_service
    app.dependency_overrides[
        get_idempotency_execution_service
    ] = lambda: idempotency_service

    # Override the database dependency used by the endpoint.
    from app.db.session import get_db

    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/trips",
                json=make_payload(),
                headers={"Idempotency-Key": "trip-create-test-001"},
            )

        assert response.status_code == 201, response.text
        assert response.json()["id"] == str(trip.id)

        trip_service.create_trip.assert_called_once()
        idempotency_service.find_existing.assert_called_once()
        idempotency_service.store_response.assert_called_once()
        db.commit.assert_called_once()
        db.rollback.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_repeated_idempotent_request_replays_existing_response():
    """A repeated request returns the saved response without creating a trip."""
    user = make_user()

    saved_body = {
        "id": str(uuid4()),
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": "2027-01-10",
        "end_date": "2027-01-15",
        "travelers": 2,
        "budget": "25000.00",
        "currency": "INR",
        "travel_style": "balanced",
        "special_requirements": None,
        "status": "draft",
        "created_at": "2026-10-24T10:00:00+00:00",
        "updated_at": "2026-10-24T10:00:00+00:00",
    }

    trip_service = Mock(spec=TripService)
    idempotency_service = Mock()
    idempotency_service.find_existing.return_value = SimpleNamespace(
        response_status=201,
        response_body=saved_body,
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_trip_service] = lambda: trip_service
    app.dependency_overrides[
        get_idempotency_execution_service
    ] = lambda: idempotency_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/trips",
                json=make_payload(),
                headers={"Idempotency-Key": "trip-create-test-002"},
            )

        assert response.status_code == 201, response.text
        assert response.json() == saved_body

        trip_service.create_trip.assert_not_called()
        idempotency_service.store_response.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_reusing_key_with_different_payload_returns_conflict():
    """A key reused for different request data returns HTTP 409."""
    user = make_user()

    trip_service = Mock(spec=TripService)
    idempotency_service = Mock()
    idempotency_service.find_existing.side_effect = (
        IdempotencyConflictError(
            "Idempotency key has already been used with a different request"
        )
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_trip_service] = lambda: trip_service
    app.dependency_overrides[
        get_idempotency_execution_service
    ] = lambda: idempotency_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/trips",
                json=make_payload(),
                headers={"Idempotency-Key": "trip-create-test-003"},
            )

        assert response.status_code == 409, response.text
        assert "different request" in response.json()["detail"]

        trip_service.create_trip.assert_not_called()
        idempotency_service.store_response.assert_not_called()
    finally:
        app.dependency_overrides.clear()
def test_concurrent_request_rolls_back_losing_trip():
    """A request that loses the key race rolls back its trip and replays the winner."""
    user = make_user()
    trip = make_trip(user.id)

    saved_body = {
        "id": str(uuid4()),
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": "2027-01-10",
        "end_date": "2027-01-15",
        "travelers": 2,
        "budget": "25000.00",
        "currency": "INR",
        "travel_style": "balanced",
        "special_requirements": None,
        "status": "draft",
        "created_at": "2026-10-24T10:00:00+00:00",
        "updated_at": "2026-10-24T10:00:00+00:00",
    }

    winning_record = SimpleNamespace(
        response_status=201,
        response_body=saved_body,
    )

    trip_service = Mock(spec=TripService)
    trip_service.create_trip.return_value = trip

    idempotency_service = Mock()
    # No record on the initial lookup; the competing request wins
    # before this request can store its idempotency response.
    idempotency_service.find_existing.side_effect = [
        None,
        winning_record,
    ]
    idempotency_service.store_response.return_value = (
        winning_record,
        False,
    )

    db = Mock()

    from app.db.session import get_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_trip_service] = lambda: trip_service
    app.dependency_overrides[
        get_idempotency_execution_service
    ] = lambda: idempotency_service
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/trips",
                json=make_payload(),
                headers={"Idempotency-Key": "trip-create-race-001"},
            )

        assert response.status_code == 201, response.text
        assert response.json() == saved_body

        trip_service.create_trip.assert_called_once()
        idempotency_service.store_response.assert_called_once()
        assert idempotency_service.find_existing.call_count == 2

        # The losing request must discard its uncommitted trip and audit event.
        db.rollback.assert_called_once()
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()
