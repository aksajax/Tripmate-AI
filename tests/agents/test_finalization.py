
"""Tests for TripMate AI workflow finalization."""

from app.graph.nodes import finalize_node
from app.graph.workflow import trip_planning_graph


def test_finalize_builds_final_itinerary():
    state = {
        "draft_itinerary": {
            "origin": "Bengaluru",
            "destination": "Goa",
            "days": [{"date": "2026-11-10", "activities": []}],
        },
        "validation_report": {
            "valid": True,
            "issues": [],
            "checks_performed": ["date_range"],
        },
        "agent_results": {
            "budget": {
                "total_budget": "25000.00",
                "currency": "INR",
                "travelers": 2,
                "budget_per_traveler": "12500.00",
                "status": "ready",
            }
        },
    }

    result = finalize_node(state)

    assert result["workflow_status"] == "completed"
    assert result["final_itinerary"]["status"] == "ready_for_review"
    assert result["final_itinerary"]["destination"] == "Goa"
    assert result["budget_summary"]["budget_per_traveler"] == "12500.00"
    assert result["completed_at"]
    assert result["current_step"] == "validation"


def test_finalize_marks_invalid_itinerary():
    state = {
        "draft_itinerary": {"days": []},
        "validation_report": {
            "valid": False,
            "issues": ["Origin is required."],
            "checks_performed": ["origin_and_destination"],
        },
        "agent_results": {},
    }

    result = finalize_node(state)

    assert result["workflow_status"] == "failed"
    assert result["final_itinerary"]["status"] == "invalid"
    assert result["final_itinerary"]["validation"]["issues"] == [
        "Origin is required."
    ]


def test_workflow_returns_final_output():
    state = {
        "trip_id": "trip-002",
        "normalized_request": {
            "origin": "Bengaluru",
            "destination": "Goa",
            "start_date": "2026-11-10",
            "end_date": "2026-11-12",
            "travelers": 2,
            "budget": "25000.00",
            "currency": "INR",
        },
        "workflow_status": "pending",
        "approval_status": "not_required",
    }

    result = trip_planning_graph.invoke(state)

    assert result["workflow_status"] == "completed"
    assert result["final_itinerary"]["destination"] == "Goa"
    assert result["budget_summary"]["total_budget"] == "25000.00"
    assert result["completed_at"]
