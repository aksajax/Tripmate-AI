
"""Regression tests for trip creation API integration."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.trips import get_trip_service
from app.main import app
from app.services.trip_service import TripService


def test_create_trip_passes_request_fields_to_service() -> None:
    """Ensure the API forwards validated fields to the trip service."""
    user_id = uuid4()
    trip_id = uuid4()

    user = SimpleNamespace(
        id=user_id,
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
    )

    expected_trip = SimpleNamespace(
        id=trip_id,
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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service = Mock(spec=TripService)
    service.create_trip.return_value = expected_trip

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_trip_service] = lambda: service

    try:
        with TestClient(app) as client:
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
                    "special_requirements": None,
                },
            )

        assert response.status_code == 201, response.text
        assert response.json()["id"] == str(trip_id)
        assert response.json()["origin"] == "Bengaluru"
        assert response.json()["destination"] == "Goa"

        service.create_trip.assert_called_once_with(
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
        )
    finally:
        app.dependency_overrides.clear()
