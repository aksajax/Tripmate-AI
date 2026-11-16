
"""Unit tests for TripMate AI tool authorization policies."""

import pytest

from app.guardrails.tool_policy import (
    TOOL_POLICIES,
    authorize_tool_operation,
    is_read_only_tool,
    is_tool_allowed,
    requires_user_approval,
)


@pytest.mark.parametrize(
    ("tool_name", "operation"),
    [
        ("destination_search", "search"),
        ("flight_search", "search"),
        ("hotel_search", "search"),
        ("weather_lookup", "forecast"),
        ("currency_lookup", "convert"),
        ("currency_lookup", "get_rate"),
        ("itinerary_save", "save_draft"),
        ("itinerary_approve", "approve"),
        ("itinerary_approve", "reject"),
    ],
)
def test_allowlisted_operations_are_permitted(
    tool_name: str,
    operation: str,
) -> None:
    assert is_tool_allowed(tool_name, operation)


@pytest.mark.parametrize(
    ("tool_name", "operation"),
    [
        ("flight_search", "book"),
        ("hotel_search", "reserve"),
        ("weather_lookup", "delete"),
        ("currency_lookup", "transfer"),
        ("payment", "charge"),
        ("unknown_tool", "execute"),
    ],
)
def test_unauthorized_operations_are_denied(
    tool_name: str,
    operation: str,
) -> None:
    assert not is_tool_allowed(tool_name, operation)

    with pytest.raises(PermissionError):
        authorize_tool_operation(tool_name, operation)


def test_approval_tool_requires_user_approval() -> None:
    assert requires_user_approval("itinerary_approve")


def test_unknown_tool_defaults_to_requiring_approval() -> None:
    assert requires_user_approval("unknown_tool")


def test_search_tools_are_read_only() -> None:
    assert is_read_only_tool("flight_search")
    assert is_read_only_tool("hotel_search")


def test_itinerary_save_is_not_read_only() -> None:
    assert not is_read_only_tool("itinerary_save")


def test_unknown_tool_is_not_read_only() -> None:
    assert not is_read_only_tool("unknown_tool")


def test_booking_and_payment_tools_are_not_allowlisted() -> None:
    assert "booking" not in TOOL_POLICIES
    assert "payment" not in TOOL_POLICIES
    assert "cancellation" not in TOOL_POLICIES
