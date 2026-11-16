
"""Integration-style tests for the compiled TripMate AI graph."""

from app.graph.routing import next_selected_agent
from app.graph.workflow import trip_planning_graph


def make_state() -> dict:
    return {
        "trip_id": "trip-001",
        "user_id": "user-001",
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
        "workflow_status": "pending",
        "approval_status": "not_required",
    }


def test_workflow_compiles():
    assert trip_planning_graph is not None


def test_workflow_runs_from_supervisor_through_validation():
    result = trip_planning_graph.invoke(make_state())

    assert result["current_step"] == "validation"
    assert result["workflow_status"] == "completed"
    assert result["validation_report"]["valid"] is True

    expected_agents = {
        "destination",
        "flights",
        "hotels",
        "weather",
        "budget",
        "itinerary",
        "validation",
    }
    assert set(result["agent_results"]) == expected_agents
    assert len(result["draft_itinerary"]["days"]) == 3


def test_workflow_keeps_provider_data_unavailable_until_connected():
    result = trip_planning_graph.invoke(make_state())

    assert (
        result["agent_results"]["flights"]["status"]
        == "provider_not_connected"
    )
    assert result["agent_results"]["flights"]["options"] == []

    assert (
        result["agent_results"]["hotels"]["status"]
        == "provider_not_connected"
    )
    assert result["agent_results"]["hotels"]["options"] == []

    assert (
        result["agent_results"]["weather"]["status"]
        == "provider_not_connected"
    )
    assert result["agent_results"]["weather"]["forecast"] is None


def test_routing_skips_unselected_agents():
    state = {
        "selected_agents": [
            "destination",
            "budget",
            "itinerary",
            "validation",
        ]
    }

    assert next_selected_agent(state, "destination") == "budget"
    assert next_selected_agent(state, "budget") == "itinerary"
    assert next_selected_agent(state, "itinerary") == "validation"
    assert next_selected_agent(state, "validation") == "end"


def test_routing_rejects_unknown_agent():
    try:
        next_selected_agent(
            {"selected_agents": ["destination", "unknown"]},
            "destination",
        )
    except ValueError as exc:
        assert "Unknown selected agents" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown agent")
