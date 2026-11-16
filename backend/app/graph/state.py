    
"""Shared state schema for the TripMate AI LangGraph workflow."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, Literal, TypedDict


def merge_agent_results(
    existing: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge agent results so parallel agents can update separate keys."""
    merged = dict(existing)
    merged.update(updates)
    return merged


class TripPlanningState(TypedDict, total=False):
    """State shared by all nodes in a TripMate AI planning run."""

    # Request and identity
    trip_id: str
    run_id: str
    thread_id: str
    user_id: str
    request: dict[str, Any]
    normalized_request: dict[str, Any]

    # Supervisor and routing
    selected_agents: list[str]
    execution_plan: list[dict[str, Any]]

    # Specialist-agent outputs.
    # The reducer combines updates from parallel agents.
    agent_results: Annotated[
        dict[str, Any],
        merge_agent_results,
    ]

    # Diagnostics and provider failures.
    errors: Annotated[
        list[dict[str, Any]],
        add,
    ]
    warnings: Annotated[
        list[str],
        add,
    ]

    # Itinerary generation and validation
    draft_itinerary: dict[str, Any]
    validation_report: dict[str, Any]
    budget_summary: dict[str, Any]

    # Human-in-the-loop review
    approval_status: Literal[
        "not_required",
        "pending",
        "approved",
        "revision_requested",
        "rejected",
    ]
    approval_id: str
    reviewed_itinerary_version: int
    revision_feedback: str
    revision_count: int

    # Workflow lifecycle
    workflow_status: Literal[
        "pending",
        "running",
        "waiting_for_approval",
        "completed",
        "failed",
        "rejected",
    ]
    current_step: str
    retry_count: int

    # Final output
    final_itinerary: dict[str, Any]
    completed_at: str
