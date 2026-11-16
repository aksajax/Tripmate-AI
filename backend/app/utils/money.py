
"""Money utilities for TripMate AI."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value: Any, *, field_name: str = "amount") -> Decimal:
    """Convert a numeric value to a finite Decimal."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a numeric amount")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid numeric amount") from None

    if not amount.is_finite():
        raise ValueError(f"{field_name} must be finite")

    return amount


def round_money(value: Any) -> Decimal:
    """Round a monetary amount to two decimal places."""
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def validate_non_negative_money(
    value: Any,
    *,
    field_name: str = "amount",
) -> Decimal:
    """Validate a non-negative amount with at most two decimal places."""
    amount = to_decimal(value, field_name=field_name)

    if amount < ZERO:
        raise ValueError(f"{field_name} cannot be negative")

    if amount.as_tuple().exponent < -2:
        raise ValueError(
            f"{field_name} cannot have more than two decimal places"
        )

    return amount.quantize(CENT)


def add_money(*values: Any) -> Decimal:
    """Add monetary amounts without floating-point arithmetic."""
    total = sum((to_decimal(value) for value in values), start=ZERO)
    return round_money(total)


def subtract_money(left: Any, right: Any) -> Decimal:
    """Subtract one monetary amount from another."""
    return round_money(to_decimal(left) - to_decimal(right))
