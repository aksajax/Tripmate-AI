
"""Unit tests for deterministic TripMate AI budget calculations."""

from decimal import Decimal

import pytest

from app.services.budget_service import calculate_budget_breakdown


def test_budget_calculates_total_and_remaining() -> None:
    result = calculate_budget_breakdown(
        Decimal("25000.00"),
        flights=Decimal("8000.00"),
        accommodation=Decimal("9000.00"),
        food=Decimal("3000.00"),
        local_transport=Decimal("1500.00"),
        activities=Decimal("2000.00"),
    )

    assert result.total_estimated == Decimal("23500.00")
    assert result.remaining == Decimal("1500.00")
    assert result.is_over_budget is False


def test_budget_detects_over_budget() -> None:
    result = calculate_budget_breakdown(
        10000,
        flights=7000,
        accommodation=5000,
    )

    assert result.total_estimated == Decimal("12000.00")
    assert result.remaining == Decimal("-2000.00")
    assert result.is_over_budget is True


def test_zero_expenses_leave_full_budget() -> None:
    result = calculate_budget_breakdown(5000)

    assert result.total_estimated == Decimal("0.00")
    assert result.remaining == Decimal("5000.00")
    assert result.is_over_budget is False


def test_exact_budget_is_not_over_budget() -> None:
    result = calculate_budget_breakdown(
        1000,
        flights=600,
        accommodation=400,
    )

    assert result.total_estimated == Decimal("1000.00")
    assert result.remaining == Decimal("0.00")
    assert result.is_over_budget is False


@pytest.mark.parametrize(
    "invalid_amount",
    [-1, "-10.00", "NaN", "Infinity", True, "invalid"],
)
def test_invalid_expense_amount_is_rejected(
    invalid_amount: object,
) -> None:
    with pytest.raises(ValueError):
        calculate_budget_breakdown(1000, flights=invalid_amount)


def test_more_than_two_decimal_places_are_rejected() -> None:
    with pytest.raises(ValueError, match="two decimal places"):
        calculate_budget_breakdown(1000, flights="12.345")


def test_budget_breakdown_is_immutable() -> None:
    result = calculate_budget_breakdown(1000)

    with pytest.raises(AttributeError):
        result.remaining = Decimal("50.00")  # type: ignore[misc]
