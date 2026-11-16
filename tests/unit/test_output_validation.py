
"""Unit tests for TripMate AI output validation guardrails."""

from app.guardrails.output_validation import validate_itinerary_output


def valid_itinerary() -> dict:
    """Return a valid example itinerary."""
    return {
        "destination": "Goa",
        "currency": "INR",
        "days": [
            {
                "date": "2027-01-10",
                "activities": ["Visit the beach"],
            }
        ],
        "total_estimated": "12500.00",
    }


def test_valid_itinerary_is_accepted() -> None:
    result = validate_itinerary_output(valid_itinerary())

    assert result.is_valid
    assert result.errors == ()


def test_non_object_output_is_rejected() -> None:
    result = validate_itinerary_output("not an itinerary")

    assert not result.is_valid
    assert "Itinerary output must be an object" in result.errors


def test_missing_required_fields_are_reported() -> None:
    result = validate_itinerary_output({})

    assert not result.is_valid
    assert len(result.errors) == 4
    assert any("destination" in error for error in result.errors)


def test_empty_destination_is_rejected() -> None:
    data = valid_itinerary()
    data["destination"] = "   "

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("destination" in error for error in result.errors)


def test_invalid_currency_is_rejected() -> None:
    data = valid_itinerary()
    data["currency"] = "inr"

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("currency" in error for error in result.errors)


def test_empty_days_list_is_rejected() -> None:
    data = valid_itinerary()
    data["days"] = []

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("days must be a non-empty list" in error for error in result.errors)


def test_day_missing_date_is_rejected() -> None:
    data = valid_itinerary()
    data["days"] = [{"activities": ["Visit the beach"]}]

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("missing date" in error for error in result.errors)


def test_activities_must_be_a_list() -> None:
    data = valid_itinerary()
    data["days"] = [{"date": "2027-01-10", "activities": "Visit the beach"}]

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("activities must be a list" in error for error in result.errors)


def test_negative_total_is_rejected() -> None:
    data = valid_itinerary()
    data["total_estimated"] = "-100"

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("non-negative amount" in error for error in result.errors)


def test_boolean_total_is_rejected() -> None:
    data = valid_itinerary()
    data["total_estimated"] = True

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("non-negative amount" in error for error in result.errors)


def test_total_with_excess_decimal_places_is_rejected() -> None:
    data = valid_itinerary()
    data["total_estimated"] = "12.345"

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("two decimal places" in error for error in result.errors)


def test_non_finite_total_is_rejected() -> None:
    data = valid_itinerary()
    data["total_estimated"] = "NaN"

    result = validate_itinerary_output(data)

    assert not result.is_valid
    assert any("non-negative amount" in error for error in result.errors)
