
"""Build and compile the TripMate AI LangGraph workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.supervisor import run_supervisor
from app.graph.error_handling import safe_node
from app.graph.nodes import (
    budget_node,
    destination_node,
    finalize_node,
    flights_node,
    hotels_node,
    itinerary_node,
    validation_node,
    weather_node,
)
from app.graph.routing import (
    route_after_budget,
    route_after_destination,
    route_after_flights,
    route_after_hotels,
    route_after_itinerary,
    route_after_validation,
    route_after_weather,
)
from app.graph.state import TripPlanningState


def _route_or_finalize(
    state: TripPlanningState,
    normal_route: Callable[[TripPlanningState], str],
) -> str:
    """Send failed workflows directly to finalization."""
    if state.get("workflow_status") == "failed":
        return "finalize"

    return normal_route(state)


def build_workflow():
    """Build and compile the TripMate AI planning graph."""
    graph = StateGraph(TripPlanningState)

    # Wrap operational nodes so unexpected errors enter graph state.
    graph.add_node("supervisor", safe_node("supervisor", run_supervisor))
    graph.add_node(
        "destination",
        safe_node("destination", destination_node),
    )
    graph.add_node("flights", safe_node("flights", flights_node))
    graph.add_node("hotels", safe_node("hotels", hotels_node))
    graph.add_node("weather", safe_node("weather", weather_node))
    graph.add_node("budget", safe_node("budget", budget_node))
    graph.add_node("itinerary", safe_node("itinerary", itinerary_node))
    graph.add_node("validation", safe_node("validation", validation_node))
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "supervisor")

    # A supervisor failure is detected by the first conditional route.
    graph.add_conditional_edges(
        "supervisor",
        lambda state: (
            "finalize"
            if state.get("workflow_status") == "failed"
            else "destination"
        ),
        {
            "destination": "destination",
            "finalize": "finalize",
        },
    )

    destinations = {
        "destination": "destination",
        "flights": "flights",
        "hotels": "hotels",
        "weather": "weather",
        "budget": "budget",
        "itinerary": "itinerary",
        "validation": "validation",
        "finalize": "finalize",
        "end": END,
    }

    graph.add_conditional_edges(
        "destination",
        lambda state: _route_or_finalize(
            state, route_after_destination
        ),
        destinations,
    )
    graph.add_conditional_edges(
        "flights",
        lambda state: _route_or_finalize(state, route_after_flights),
        destinations,
    )
    graph.add_conditional_edges(
        "hotels",
        lambda state: _route_or_finalize(state, route_after_hotels),
        destinations,
    )
    graph.add_conditional_edges(
        "weather",
        lambda state: _route_or_finalize(state, route_after_weather),
        destinations,
    )
    graph.add_conditional_edges(
        "budget",
        lambda state: _route_or_finalize(state, route_after_budget),
        destinations,
    )
    graph.add_conditional_edges(
        "itinerary",
        lambda state: _route_or_finalize(state, route_after_itinerary),
        destinations,
    )
    graph.add_conditional_edges(
        "validation",
        lambda state: _route_or_finalize(state, route_after_validation),
        destinations,
    )

    graph.add_edge("finalize", END)

    return graph.compile()


trip_planning_graph = build_workflow()
