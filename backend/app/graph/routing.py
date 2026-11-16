
"""Conditional routing helpers for the TripMate AI workflow."""

from __future__ import annotations

from app.graph.state import TripPlanningState


AGENT_ORDER = (
    "destination",
    "flights",
    "hotels",
    "weather",
    "budget",
    "itinerary",
    "validation",
)


def next_selected_agent(
    state: TripPlanningState,
    current_agent: str,
) -> str:
    """Return the next selected agent after the current agent."""
    if current_agent not in AGENT_ORDER:
        raise ValueError(f"Unknown current agent: {current_agent}")

    selected = state.get("selected_agents", [])
    if not isinstance(selected, list):
        raise ValueError("selected_agents must be a list")

    unknown = set(selected) - set(AGENT_ORDER)
    if unknown:
        raise ValueError(
            f"Unknown selected agents: {', '.join(sorted(unknown))}"
        )

    current_index = AGENT_ORDER.index(current_agent)

    for agent in AGENT_ORDER[current_index + 1 :]:
        if agent in selected:
            return agent

    return "end"


def route_after_destination(state: TripPlanningState) -> str:
    return next_selected_agent(state, "destination")


def route_after_flights(state: TripPlanningState) -> str:
    return next_selected_agent(state, "flights")


def route_after_hotels(state: TripPlanningState) -> str:
    return next_selected_agent(state, "hotels")


def route_after_weather(state: TripPlanningState) -> str:
    return next_selected_agent(state, "weather")


def route_after_budget(state: TripPlanningState) -> str:
    return next_selected_agent(state, "budget")


def route_after_itinerary(state: TripPlanningState) -> str:
    return next_selected_agent(state, "itinerary")



def route_after_validation(state: TripPlanningState) -> str:
    """Always pass the validation result to finalization."""
    return "finalize"

