
"""Tests for TripMate AI shared graph state."""

from app.graph.state import (
    TripPlanningState,
    merge_agent_results,
)


def test_merge_agent_results_preserves_existing_results():
    """Results from different agents should coexist."""
    existing = {
        "destination": {"name": "Goa"},
        "weather": {"condition": "sunny"},
    }
    updates = {
        "flights": {"currency": "INR"},
    }

    merged = merge_agent_results(existing, updates)

    assert merged == {
        "destination": {"name": "Goa"},
        "weather": {"condition": "sunny"},
        "flights": {"currency": "INR"},
    }


def test_merge_agent_results_updates_matching_key():
    """A new result should replace an older result for the same agent."""
    existing = {"weather": {"condition": "sunny"}}
    updates = {"weather": {"condition": "cloudy"}}

    merged = merge_agent_results(existing, updates)

    assert merged["weather"]["condition"] == "cloudy"
    assert existing["weather"]["condition"] == "sunny"


def test_graph_state_accepts_trip_request():
    """The state should support a basic normalized trip request."""
    state: TripPlanningState = {
        "trip_id": "trip-001",
        "user_id": "user-001",
        "normalized_request": {
            "origin": "Bengaluru",
            "destination": "Goa",
            "travelers": 2,
        },
        "selected_agents": ["destination", "weather", "budget"],
        "workflow_status": "pending",
        "approval_status": "not_required",
    }

    assert state["trip_id"] == "trip-001"
    assert state["normalized_request"]["destination"] == "Goa"
    assert "weather" in state["selected_agents"]


def test_graph_state_supports_pending_approval():
    """The state should represent a draft waiting for human review."""
    state: TripPlanningState = {
        "workflow_status": "waiting_for_approval",
        "approval_status": "pending",
        "draft_itinerary": {"days": []},
        "reviewed_itinerary_version": 1,
    }

    assert state["workflow_status"] == "waiting_for_approval"
    assert state["approval_status"] == "pending"
    assert state["reviewed_itinerary_version"] == 1
