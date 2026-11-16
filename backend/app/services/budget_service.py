
"""Deterministic budget calculations for TripMate AI."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _to_money(value: Any, field_name: str) -> Decimal:
    """Convert a numeric value to a validated two-decimal money amount."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a monetary amount")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid monetary amount") from None

    if not amount.is_finite():
        raise ValueError(f"{field_name} must be finite")

    if amount < ZERO:
        raise ValueError(f"{field_name} cannot be negative")

    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{field_name} cannot have more than two decimal places")

    return amount.quantize(CENT)


@dataclass(frozen=True)
class BudgetBreakdown:
    """Immutable summary of a trip's estimated expenses."""

    budget: Decimal
    flights: Decimal
    accommodation: Decimal
    food: Decimal
    local_transport: Decimal
    activities: Decimal
    other: Decimal
    total_estimated: Decimal
    remaining: Decimal
    is_over_budget: bool


def calculate_budget_breakdown(
    budget: Any,
    *,
    flights: Any = ZERO,
    accommodation: Any = ZERO,
    food: Any = ZERO,
    local_transport: Any = ZERO,
    activities: Any = ZERO,
    other: Any = ZERO,
) -> BudgetBreakdown:
    """Calculate expense totals and remaining budget without float arithmetic.

    Negative remaining amounts are retained to show how far an itinerary
    exceeds the budget. This function never changes or hides expense values.
    """
    amounts = {
        "budget": _to_money(budget, "budget"),
        "flights": _to_money(flights, "flights"),
        "accommodation": _to_money(accommodation, "accommodation"),
        "food": _to_money(food, "food"),
        "local_transport": _to_money(local_transport, "local_transport"),
        "activities": _to_money(activities, "activities"),
        "other": _to_money(other, "other"),
    }

    total_estimated = sum(
        (
            amounts["flights"],
            amounts["accommodation"],
            amounts["food"],
            amounts["local_transport"],
            amounts["activities"],
            amounts["other"],
        ),
        start=ZERO,
    ).quantize(CENT)

    remaining = (amounts["budget"] - total_estimated).quantize(CENT)

    return BudgetBreakdown(
        **amounts,
        total_estimated=total_estimated,
        remaining=remaining,
        is_over_budget=total_estimated > amounts["budget"],
    )
