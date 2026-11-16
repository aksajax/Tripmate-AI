
"""End-to-end integration tests for the TripMate AI graph."""

from app.graph.workflow import trip_planning_graph


def valid_trip_request():
    return {
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": "2026-11-01",
        "end_date": "2026-11-03",
        "budget": "25000.00",
        "currency": "INR",
        "travelers": 2,
        "transport_required": True,
        "accommodation_required": True,
        "include_weather": True,
    }


def test_graph_generates_final_itinerary():
    initial_state = {
        "request": valid_trip_request(),
        "run_id": "integration-test-run",
        "thread_id": "integration-test-thread",
        "user_id": "integration-test-user",
        "workflow_status": "pending",
    }

    result = trip_planning_graph.invoke(initial_state)

    assert result["workflow_status"] == "completed"
    assert result["current_step"] == "validation"
    assert result["validation_report"]["valid"] is True

    assert result["final_itinerary"] is not None
    assert result["final_itinerary"]["status"] == "ready_for_review"

    assert result["budget_summary"]["total_budget"] == "25000.00"
    assert result["budget_summary"]["currency"] == "INR"
    assert result["budget_summary"]["travelers"] == 2

    assert result["errors"] == []


def test_graph_records_selected_agents():
    initial_state = {
        "request": valid_trip_request(),
        "run_id": "agent-selection-test",
        "thread_id": "agent-selection-thread",
        "user_id": "integration-test-user",
        "workflow_status": "pending",
    }

    result = trip_planning_graph.invoke(initial_state)

    selected_agents = result["selected_agents"]

    assert "destination" in selected_agents
    assert "budget" in selected_agents
    assert "itinerary" in selected_agents
    assert "validation" in selected_agents

    assert result["agent_results"]["destination"]["status"] == "ready"
    assert result["agent_results"]["budget"]["status"] == "ready"
