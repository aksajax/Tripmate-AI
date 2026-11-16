
"""Unit tests for TripMate AI trip request schemas."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.trip import TripCreate


@pytest.fixture
def valid_trip_data() -> dict:
    """Return a valid trip request for reuse across tests."""
    return {
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": date(2027, 1, 10),
        "end_date": date(2027, 1, 15),
        "travelers": 2,
        "budget": Decimal("25000.00"),
        "currency": "INR",
        "travel_style": "balanced",
    }


def test_valid_trip_request_is_accepted(valid_trip_data: dict) -> None:
    trip = TripCreate(**valid_trip_data)

    assert trip.origin == "Bengaluru"
    assert trip.destination == "Goa"
    assert trip.travelers == 2
    assert trip.budget == Decimal("25000.00")
    assert trip.currency == "INR"


def test_same_origin_and_destination_are_rejected(
    valid_trip_data: dict,
) -> None:
    valid_trip_data["destination"] = "Bengaluru"

    with pytest.raises(ValidationError):
        TripCreate(**valid_trip_data)


def test_end_date_before_start_date_is_rejected(
    valid_trip_data: dict,
) -> None:
    valid_trip_data["end_date"] = date(2027, 1, 9)

    with pytest.raises(ValidationError):
        TripCreate(**valid_trip_data)


@pytest.mark.parametrize("travelers", [0, -1, 13])
def test_invalid_traveler_count_is_rejected(
    valid_trip_data: dict,
    travelers: int,
) -> None:
    valid_trip_data["travelers"] = travelers

    with pytest.raises(ValidationError):
        TripCreate(**valid_trip_data)


@pytest.mark.parametrize("currency", ["XYZ", "IN", "USDD"])
def test_unsupported_currency_is_rejected(
    valid_trip_data: dict,
    currency: str,
) -> None:
    valid_trip_data["currency"] = currency

    with pytest.raises(ValidationError):
        TripCreate(**valid_trip_data)


def test_negative_budget_is_rejected(valid_trip_data: dict) -> None:
    valid_trip_data["budget"] = Decimal("-100.00")

    with pytest.raises(ValidationError):
        TripCreate(**valid_trip_data)


def test_unknown_fields_are_rejected(valid_trip_data: dict) -> None:
    valid_trip_data["unexpected_field"] = "not allowed"

    with pytest.raises(ValidationError):
        TripCreate(**valid_trip_data)
