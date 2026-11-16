
"""Tool authorization policy for TripMate AI agents."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPolicy:
    """Describe a tool and the operations it is permitted to perform."""

    name: str
    allowed_operations: frozenset[str]
    requires_user_approval: bool = False
    read_only: bool = True


# The first release is planning-only. No booking, payment, or cancellation
# tools are authorized.
TOOL_POLICIES: dict[str, ToolPolicy] = {
    "destination_search": ToolPolicy(
        name="destination_search",
        allowed_operations=frozenset({"search"}),
    ),
    "flight_search": ToolPolicy(
        name="flight_search",
        allowed_operations=frozenset({"search"}),
    ),
    "hotel_search": ToolPolicy(
        name="hotel_search",
        allowed_operations=frozenset({"search"}),
    ),
    "weather_lookup": ToolPolicy(
        name="weather_lookup",
        allowed_operations=frozenset({"forecast"}),
    ),
    "currency_lookup": ToolPolicy(
        name="currency_lookup",
        allowed_operations=frozenset({"convert", "get_rate"}),
    ),
    "itinerary_save": ToolPolicy(
        name="itinerary_save",
        allowed_operations=frozenset({"save_draft"}),
        requires_user_approval=False,
        read_only=False,
    ),
    "itinerary_approve": ToolPolicy(
        name="itinerary_approve",
        allowed_operations=frozenset({"approve", "reject"}),
        requires_user_approval=True,
        read_only=False,
    ),
}


def is_tool_allowed(tool_name: str, operation: str) -> bool:
    """Return whether a tool operation is explicitly allowlisted."""
    policy = TOOL_POLICIES.get(tool_name)

    if policy is None:
        return False

    return operation in policy.allowed_operations


def requires_user_approval(tool_name: str) -> bool:
    """Return whether a tool's operation requires human approval."""
    policy = TOOL_POLICIES.get(tool_name)
    return policy.requires_user_approval if policy else True


def is_read_only_tool(tool_name: str) -> bool:
    """Return whether a known tool is declared read-only."""
    policy = TOOL_POLICIES.get(tool_name)
    return policy.read_only if policy else False


def authorize_tool_operation(tool_name: str, operation: str) -> None:
    """Raise PermissionError when a requested operation is not allowlisted."""
    if not is_tool_allowed(tool_name, operation):
        raise PermissionError(
            f"Tool operation is not authorized: {tool_name}.{operation}"
        )
