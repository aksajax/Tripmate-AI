
"""Deterministic supervisor for the TripMate AI multi-agent workflow."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.graph.state import TripPlanningState


class SupervisorAgent:
    """Select specialist agents using predictable routing rules."""

    REQUIRED_AGENTS = (
        "destination",
        "budget",
        "itinerary",
        "validation",
    )

    OPTIONAL_AGENTS = (
        "flights",
        "hotels",
        "weather",
    )

    AGENT_PURPOSES = {
        "destination": "Collect destination information and travel highlights.",
        "flights": "Research suitable transport or flight options.",
        "hotels": "Research accommodation options for the trip.",
        "weather": "Check weather information for the destination and dates.",
        "budget": "Estimate costs and check the requested budget.",
        "itinerary": "Build a day-by-day travel itinerary.",
        "validation": "Validate the itinerary, dates, and budget calculations.",
    }

    @staticmethod
    def _has_value(value: Any) -> bool:
        """Return True when a value is present and non-empty."""
        return value is not None and str(value).strip() != ""

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        """Parse a date or ISO-formatted date string safely."""
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str) and value.strip():
            try:
                return date.fromisoformat(value.strip()[:10])
            except ValueError:
                return None

        return None

    def select_agents(self, request: dict[str, Any]) -> list[str]:
        """Return the ordered list of agents relevant to a trip request."""
        if not isinstance(request, dict):
            raise TypeError("request must be a dictionary")

        selected = list(self.REQUIRED_AGENTS)

        origin = request.get("origin")
        destination = request.get("destination")

        # Transport planning requires both endpoints.
        if (
            self._has_value(origin)
            and self._has_value(destination)
            and request.get("transport_required", True) is not False
        ):
            selected.append("flights")

        # Accommodation is relevant when the trip includes an overnight stay.
        start_date = self._parse_date(
            request.get("start_date", request.get("departure_date"))
        )
        end_date = self._parse_date(
            request.get("end_date", request.get("return_date"))
        )

        if (
            start_date is not None
            and end_date is not None
            and end_date > start_date
            and request.get("accommodation_required", True) is not False
        ):
            selected.append("hotels")

        # Weather is useful when there is a known destination.
        if (
            self._has_value(destination)
            and request.get("include_weather", True) is not False
        ):
            selected.append("weather")

        # Keep the order stable for reproducible runs and tests.
        order = (
            "destination",
            "flights",
            "hotels",
            "weather",
            "budget",
            "itinerary",
            "validation",
        )
        return [agent for agent in order if agent in selected]

    def build_execution_plan(
        self,
        selected_agents: list[str],
    ) -> list[dict[str, str]]:
        """Create a readable execution plan for the selected agents."""
        unknown_agents = set(selected_agents) - set(self.AGENT_PURPOSES)

        if unknown_agents:
            raise ValueError(
                f"Unknown agent names: {', '.join(sorted(unknown_agents))}"
            )

        return [
            {
                "agent": agent,
                "purpose": self.AGENT_PURPOSES[agent],
            }
            for agent in selected_agents
        ]

    def run(self, state: TripPlanningState) -> dict[str, Any]:
        """Return the state updates produced by the supervisor node."""
        request = state.get("normalized_request") or state.get("request")

        if not isinstance(request, dict):
            raise ValueError(
                "Graph state must contain a normalized_request or request dictionary"
            )

        selected_agents = self.select_agents(request)

        return {
            "selected_agents": selected_agents,
            "execution_plan": self.build_execution_plan(selected_agents),
            "current_step": "supervisor",
            "workflow_status": "running",
        }


def run_supervisor(state: TripPlanningState) -> dict[str, Any]:
    """Convenience function for use as a LangGraph node."""
    return SupervisorAgent().run(state)
