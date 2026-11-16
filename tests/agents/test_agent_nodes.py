
"""Tests for TripMate AI specialist graph nodes."""

from datetime import date
from decimal import Decimal

from app.graph.nodes import (
    budget_node,
    destination_node,
    flights_node,
    hotels_node,
    itinerary_node,
    validation_node,
    weather_node,
)


def make_state() -> dict:
    return {
        "trip_id": "trip-001",
        "normalized_request": {
            "origin": "Bengaluru",
            "destination": "Goa",
            "start_date": "2026-11-10",
            "end_date": "2026-11-12",
            "travelers": 2,
            "budget": "25000.00",
            "currency": "INR",
            "travel_style": "balanced",
        },
        "workflow_status": "running",
    }


def test_destination_node_uses_request_data():
    result = destination_node(make_state())
    destination = result["agent_results"]["destination"]

    assert destination["origin"] == "Bengaluru"
    assert destination["destination"] == "Goa"
    assert destination["status"] == "ready"
    assert destination["source"] == "user_request"


def test_flights_node_does_not_invent_flight_options():
    result = flights_node(make_state())
    flights = result["agent_results"]["flights"]

    assert flights["status"] == "provider_not_connected"
    assert flights["options"] == []
    assert flights["origin"] == "Bengaluru"


def test_hotels_node_does_not_invent_hotel_options():
    result = hotels_node(make_state())
    hotels = result["agent_results"]["hotels"]

    assert hotels["status"] == "provider_not_connected"
    assert hotels["options"] == []
    assert hotels["destination"] == "Goa"


def test_weather_node_does_not_invent_forecast():
    result = weather_node(make_state())
    weather = result["agent_results"]["weather"]

    assert weather["status"] == "provider_not_connected"
    assert weather["forecast"] is None


def test_budget_node_calculates_budget_per_traveler():
    result = budget_node(make_state())
    budget = result["agent_results"]["budget"]

    assert Decimal(budget["total_budget"]) == Decimal("25000.00")
    assert budget["budget_per_traveler"] == "12500.00"
    assert budget["currency"] == "INR"
    assert budget["status"] == "ready"


def test_budget_node_rejects_negative_budget():
    state = make_state()
    state["normalized_request"]["budget"] = "-100"

    result = budget_node(state)
    budget = result["agent_results"]["budget"]

    assert budget["status"] == "needs_input"
    assert "Budget cannot be negative." in budget["errors"]


def test_itinerary_node_creates_date_only_draft():
    result = itinerary_node(make_state())
    draft = result["draft_itinerary"]

    assert draft["status"] == "draft"
    assert len(draft["days"]) == 3
    assert draft["days"][0]["date"] == "2026-11-10"
    assert draft["days"][-1]["date"] == "2026-11-12"
    assert all(day["activities"] == [] for day in draft["days"])


def test_itinerary_node_supports_date_objects():
    state = make_state()
    state["normalized_request"]["start_date"] = date(2026, 11, 10)
    state["normalized_request"]["end_date"] = date(2026, 11, 11)

    result = itinerary_node(state)

    assert len(result["draft_itinerary"]["days"]) == 2


def test_validation_node_accepts_valid_request():
    result = validation_node(make_state())

    assert result["validation_report"]["valid"] is True
    assert result["validation_report"]["issues"] == []
    assert result["agent_results"]["validation"]["status"] == "passed"


def test_validation_node_detects_same_origin_and_destination():
    state = make_state()
    state["normalized_request"]["destination"] = " bengaluru "

    result = validation_node(state)

    assert result["validation_report"]["valid"] is False
    assert (
        "Origin and destination must be different."
        in result["validation_report"]["issues"]
    )


def test_validation_node_detects_invalid_date_order():
    state = make_state()
    state["normalized_request"]["start_date"] = "2026-11-15"
    state["normalized_request"]["end_date"] = "2026-11-12"

    result = validation_node(state)

    assert result["validation_report"]["valid"] is False
    assert (
        "End date must be on or after the start date."
        in result["validation_report"]["issues"]
    )


def test_validation_node_detects_invalid_traveler_count():
    state = make_state()
    state["normalized_request"]["travelers"] = 20

    result = validation_node(state)

    assert result["validation_report"]["valid"] is False
    assert (
        "Travelers must be an integer between 1 and 12."
        in result["validation_report"]["issues"]
    )


def test_nodes_require_a_trip_request():
    try:
        destination_node({})
    except ValueError as exc:
        assert "trip request dictionary" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing trip request")
