
"""Unit tests for TripMate AI money utilities."""

from decimal import Decimal

import pytest

from app.utils.money import (
    add_money,
    round_money,
    subtract_money,
    to_decimal,
    validate_non_negative_money,
)


def test_round_money_uses_half_up_rounding() -> None:
    assert round_money("12.345") == Decimal("12.35")
    assert round_money("12.344") == Decimal("12.34")


def test_add_money_avoids_float_arithmetic() -> None:
    assert add_money("10.10", "20.20", "0.70") == Decimal("31.00")


def test_subtract_money_returns_correct_difference() -> None:
    assert subtract_money("50.00", "12.50") == Decimal("37.50")


def test_to_decimal_accepts_integer_and_decimal() -> None:
    assert to_decimal(10) == Decimal("10")
    assert to_decimal(Decimal("20.50")) == Decimal("20.50")


def test_validate_non_negative_money_accepts_valid_amount() -> None:
    assert validate_non_negative_money("100.00") == Decimal("100.00")


@pytest.mark.parametrize(
    "value",
    ["-1.00", "1.234", "NaN", "Infinity", "-Infinity", True, "invalid"],
)
def test_validate_non_negative_money_rejects_invalid_values(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        validate_non_negative_money(value)


def test_round_money_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        round_money("NaN")


def test_empty_addition_returns_zero() -> None:
    assert add_money() == Decimal("0.00")
