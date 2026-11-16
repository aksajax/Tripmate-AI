
"""Tests for the TripMate AI supervisor agent."""

import pytest

from app.agents.supervisor import SupervisorAgent, run_supervisor


@pytest.fixture
def supervisor() -> SupervisorAgent:
    return SupervisorAgent()


@pytest.fixture
def complete_request() -> dict:
    return {
        "origin": "Bengaluru",
        "destination": "Goa",
        "start_date": "2026-11-10",
        "end_date": "2026-11-14",
        "travelers": 2,
        "budget": "25000.00",
        "currency": "INR",
    }


def test_selects_expected_agents_for_multi_day_trip(
    supervisor: SupervisorAgent,
    complete_request: dict,
):
    agents = supervisor.select_agents(complete_request)

    assert agents == [
        "destination",
        "flights",
        "hotels",
        "weather",
        "budget",
        "itinerary",
        "validation",
    ]


def test_always_selects_core_agents(supervisor: SupervisorAgent):
    agents = supervisor.select_agents({})

    assert agents == [
        "destination",
        "budget",
        "itinerary",
        "validation",
    ]


def test_skips_flights_when_transport_is_disabled(
    supervisor: SupervisorAgent,
    complete_request: dict,
):
    complete_request["transport_required"] = False

    agents = supervisor.select_agents(complete_request)

    assert "flights" not in agents


def test_skips_hotels_for_same_day_trip(
    supervisor: SupervisorAgent,
    complete_request: dict,
):
    complete_request["end_date"] = complete_request["start_date"]

    agents = supervisor.select_agents(complete_request)

    assert "hotels" not in agents


def test_skips_weather_when_disabled(
    supervisor: SupervisorAgent,
    complete_request: dict,
):
    complete_request["include_weather"] = False

    agents = supervisor.select_agents(complete_request)

    assert "weather" not in agents


def test_rejects_non_dictionary_request(supervisor: SupervisorAgent):
    with pytest.raises(TypeError, match="request must be a dictionary"):
        supervisor.select_agents("plan my trip")  # type: ignore[arg-type]


def test_execution_plan_contains_agent_purposes(
    supervisor: SupervisorAgent,
):
    plan = supervisor.build_execution_plan(["destination", "budget"])

    assert plan == [
        {
            "agent": "destination",
            "purpose": (
                "Collect destination information and travel highlights."
            ),
        },
        {
            "agent": "budget",
            "purpose": (
                "Estimate costs and check the requested budget."
            ),
        },
    ]


def test_execution_plan_rejects_unknown_agent(
    supervisor: SupervisorAgent,
):
    with pytest.raises(ValueError, match="Unknown agent names"):
        supervisor.build_execution_plan(["unknown_agent"])


def test_run_returns_graph_state_updates(
    complete_request: dict,
):
    state = {
        "trip_id": "trip-001",
        "normalized_request": complete_request,
        "workflow_status": "pending",
    }

    updates = run_supervisor(state)

    assert "flights" in updates["selected_agents"]
    assert "hotels" in updates["selected_agents"]
    assert updates["current_step"] == "supervisor"
    assert updates["workflow_status"] == "running"
    assert len(updates["execution_plan"]) == len(
        updates["selected_agents"]
    )


def test_run_uses_original_request_when_normalized_request_is_missing():
    state = {
        "request": {
            "origin": "Bengaluru",
            "destination": "Mysuru",
        }
    }

    updates = run_supervisor(state)

    assert "flights" in updates["selected_agents"]
    assert "weather" in updates["selected_agents"]


def test_run_requires_a_request_dictionary():
    with pytest.raises(ValueError, match="must contain a normalized_request"):
        run_supervisor({})
