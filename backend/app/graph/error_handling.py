
"""Error handling utilities for TripMate AI graph nodes."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.graph.state import TripPlanningState

logger = logging.getLogger(__name__)

GraphNode = Callable[
    [TripPlanningState],
    dict[str, Any],
]


def safe_node(
    node_name: str,
    node: GraphNode,
) -> GraphNode:
    """Wrap a graph node and convert unexpected exceptions to state updates."""

    def wrapped(state: TripPlanningState) -> dict[str, Any]:
        try:
            return node(state)
        except Exception as exc:
            logger.exception(
                "TripMate AI graph node failed: %s",
                node_name,
            )

            return {
                "current_step": node_name,
                "workflow_status": "failed",
                "errors": [
                    {
                        "node": node_name,
                        "error_type": type(exc).__name__,
                        "message": str(exc) or "Unexpected node failure.",
                    }
                ],
            }

    return wrapped
