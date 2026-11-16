
"""Specialist node functions for the TripMate AI graph."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.graph.state import TripPlanningState


def _get_request(state: TripPlanningState) -> dict[str, Any]:
    """Get the normalized request, falling back to the original request."""
    request = state.get("normalized_request") or state.get("request")

    if not isinstance(request, dict):
        raise ValueError("Graph state must contain a trip request dictionary")

    return request


def _parse_date(value: Any) -> date | None:
    """Parse date, datetime, or ISO-formatted date values."""
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


def _decimal_value(value: Any) -> Decimal | None:
    """Convert a value to Decimal without silently accepting invalid input."""
    if value is None or isinstance(value, bool):
        return None

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not result.is_finite():
        return None

    return result


def destination_node(state: TripPlanningState) -> dict[str, Any]:
    """Prepare destination context from user-provided information."""
    request = _get_request(state)
    destination = request.get("destination")

    return {
        "agent_results": {
            "destination": {
                "destination": destination,
                "origin": request.get("origin"),
                "travel_style": request.get("travel_style", "balanced"),
                "special_requirements": request.get(
                    "special_requirements"
                ),
                "status": (
                    "ready"
                    if isinstance(destination, str) and destination.strip()
                    else "needs_input"
                ),
                "source": "user_request",
            }
        }
    }


def flights_node(state: TripPlanningState) -> dict[str, Any]:
    """Represent the flight search task without inventing flight results."""
    request = _get_request(state)

    return {
        "agent_results": {
            "flights": {
                "origin": request.get("origin"),
                "destination": request.get("destination"),
                "departure_date": request.get(
                    "start_date", request.get("departure_date")
                ),
                "return_date": request.get(
                    "end_date", request.get("return_date")
                ),
                "status": "provider_not_connected",
                "options": [],
                "message": (
                    "Flight options are unavailable until a flight provider "
                    "is configured."
                ),
            }
        }
    }


def hotels_node(state: TripPlanningState) -> dict[str, Any]:
    """Represent the hotel search task without inventing hotel results."""
    request = _get_request(state)

    return {
        "agent_results": {
            "hotels": {
                "destination": request.get("destination"),
                "check_in": request.get(
                    "start_date", request.get("departure_date")
                ),
                "check_out": request.get(
                    "end_date", request.get("return_date")
                ),
                "travelers": request.get("travelers", 1),
                "status": "provider_not_connected",
                "options": [],
                "message": (
                    "Accommodation options are unavailable until a hotel "
                    "provider is configured."
                ),
            }
        }
    }


def weather_node(state: TripPlanningState) -> dict[str, Any]:
    """Represent the weather lookup task without inventing a forecast."""
    request = _get_request(state)

    return {
        "agent_results": {
            "weather": {
                "destination": request.get("destination"),
                "start_date": request.get(
                    "start_date", request.get("departure_date")
                ),
                "end_date": request.get("end_date", request.get("return_date")),
                "status": "provider_not_connected",
                "forecast": None,
                "message": (
                    "Weather information is unavailable until a weather "
                    "provider is configured."
                ),
            }
        }
    }


def budget_node(state: TripPlanningState) -> dict[str, Any]:
    """Calculate deterministic budget information from the trip request."""
    request = _get_request(state)

    raw_budget = request.get("budget")
    budget = _decimal_value(raw_budget)
    travelers = request.get("travelers", 1)

    errors: list[str] = []

    if budget is None:
        errors.append("A valid budget has not been provided.")
    elif budget < 0:
        errors.append("Budget cannot be negative.")

    if isinstance(travelers, bool) or not isinstance(travelers, int):
        errors.append("Travelers must be an integer.")
        travelers = None
    elif travelers < 1:
        errors.append("Travelers must be at least 1.")
        travelers = None

    budget_per_traveler = None
    if budget is not None and budget >= 0 and travelers:
        budget_per_traveler = str(
            (budget / Decimal(travelers)).quantize(Decimal("0.01"))
        )

    return {
        "agent_results": {
            "budget": {
                "total_budget": str(budget) if budget is not None else None,
                "currency": request.get("currency", "INR"),
                "travelers": travelers,
                "budget_per_traveler": budget_per_traveler,
                "status": "ready" if not errors else "needs_input",
                "errors": errors,
                "source": "user_request",
                "note": (
                    "This is budget arithmetic only; no travel prices have "
                    "been estimated."
                ),
            }
        }
    }


def itinerary_node(state: TripPlanningState) -> dict[str, Any]:
    """Create a transparent itinerary draft structure for later enrichment."""
    request = _get_request(state)

    start_date = _parse_date(
        request.get("start_date", request.get("departure_date"))
    )
    end_date = _parse_date(
        request.get("end_date", request.get("return_date"))
    )

    days: list[dict[str, Any]] = []

    if start_date and end_date and end_date >= start_date:
        current_date = start_date
        while current_date <= end_date:
            days.append(
                {
                    "date": current_date.isoformat(),
                    "activities": [],
                    "status": "awaiting_research",
                }
            )
            current_date = date.fromordinal(current_date.toordinal() + 1)

    draft = {
        "origin": request.get("origin"),
        "destination": request.get("destination"),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "travelers": request.get("travelers", 1),
        "currency": request.get("currency", "INR"),
        "days": days,
        "status": "draft",
        "message": (
            "This draft contains dates only. Activities will be added after "
            "destination research and provider integrations are available."
        ),
    }

    return {
        "draft_itinerary": draft,
        "agent_results": {
            "itinerary": {
                "status": "draft_created",
                "day_count": len(days),
            }
        },
    }



def validation_node(state: TripPlanningState) -> dict[str, Any]:
    """Validate the trip and record the final workflow status."""
    request = _get_request(state)
    issues: list[str] = []

    origin = request.get("origin")
    destination = request.get("destination")

    if not isinstance(origin, str) or not origin.strip():
        issues.append("Origin is required.")

    if not isinstance(destination, str) or not destination.strip():
        issues.append("Destination is required.")
    elif (
        isinstance(origin, str)
        and origin.strip().casefold() == destination.strip().casefold()
    ):
        issues.append("Origin and destination must be different.")

    start_date = _parse_date(
        request.get("start_date", request.get("departure_date"))
    )
    end_date = _parse_date(
        request.get("end_date", request.get("return_date"))
    )

    if start_date is None:
        issues.append("A valid start date is required.")

    if end_date is None:
        issues.append("A valid end date is required.")
    elif start_date is not None and end_date < start_date:
        issues.append("End date must be on or after the start date.")

    budget = _decimal_value(request.get("budget"))

    if budget is None:
        issues.append("A valid budget is required.")
    elif budget < 0:
        issues.append("Budget cannot be negative.")

    travelers = request.get("travelers", 1)
    if (
        isinstance(travelers, bool)
        or not isinstance(travelers, int)
        or not 1 <= travelers <= 12
    ):
        issues.append("Travelers must be an integer between 1 and 12.")

    is_valid = not issues

    report = {
        "valid": is_valid,
        "issues": issues,
        "checks_performed": [
            "origin_and_destination",
            "date_range",
            "budget",
            "traveler_count",
        ],
    }

    return {
        "current_step": "validation",
        "workflow_status": "completed" if is_valid else "failed",
        "validation_report": report,
        "agent_results": {
            "validation": {
                "status": "passed" if is_valid else "failed",
                "issue_count": len(issues),
            }
        },
    }

def finalize_node(state: TripPlanningState) -> dict[str, Any]:
    """Build the final workflow response from the available state."""
    from datetime import datetime, timezone

    validation_report = state.get("validation_report") or {
        "valid": False,
        "issues": ["Validation did not produce a report."],
        "checks_performed": [],
    }

    draft = state.get("draft_itinerary") or {}
    agent_results = state.get("agent_results") or {}
    budget_result = agent_results.get("budget") or {}

    is_valid = validation_report.get("valid") is True

    budget_summary = {
        "total_budget": budget_result.get("total_budget"),
        "currency": budget_result.get("currency"),
        "travelers": budget_result.get("travelers"),
        "budget_per_traveler": budget_result.get("budget_per_traveler"),
        "status": budget_result.get("status", "unavailable"),
    }

    final_itinerary = {
        **draft,
        "validation": validation_report,
        "budget_summary": budget_summary,
        "agent_results": agent_results,
        "status": "ready_for_review" if is_valid else "invalid",
    }

    return {
        "final_itinerary": final_itinerary,
        "budget_summary": budget_summary,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "workflow_status": "completed" if is_valid else "failed",
        # Keep this as "validation" for compatibility with existing tests.
        "current_step": "validation",
    }

