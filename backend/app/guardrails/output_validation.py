
"""Output validation guardrails for TripMate AI."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class OutputValidationResult:
    """Validation result for structured itinerary output."""

    is_valid: bool
    errors: tuple[str, ...]


_REQUIRED_ITINERARY_FIELDS = {
    "destination",
    "currency",
    "days",
    "total_estimated",
}


def validate_itinerary_output(
    output: Any,
) -> OutputValidationResult:
    """Validate the basic structure of a generated itinerary."""
    errors: list[str] = []

    if not isinstance(output, dict):
        return OutputValidationResult(
            is_valid=False,
            errors=("Itinerary output must be an object",),
        )

    missing_fields = _REQUIRED_ITINERARY_FIELDS - output.keys()

    for field in sorted(missing_fields):
        errors.append(f"Missing required field: {field}")

    destination = output.get("destination")
    if "destination" in output:
        if not isinstance(destination, str) or not destination.strip():
            errors.append("destination must be a non-empty string")

    currency = output.get("currency")
    if "currency" in output:
        if (
            not isinstance(currency, str)
            or len(currency) != 3
            or not currency.isalpha()
            or currency != currency.upper()
        ):
            errors.append("currency must be a three-letter uppercase code")

    days = output.get("days")
    if "days" in output:
        if not isinstance(days, list) or not days:
            errors.append("days must be a non-empty list")
        else:
            for index, day in enumerate(days):
                if not isinstance(day, dict):
                    errors.append(f"days[{index}] must be an object")
                    continue

                if "date" not in day:
                    errors.append(f"days[{index}] is missing date")

                activities = day.get("activities")
                if not isinstance(activities, list):
                    errors.append(
                        f"days[{index}].activities must be a list"
                    )

    if "total_estimated" in output:
        amount = output["total_estimated"]

        if isinstance(amount, bool):
            errors.append("total_estimated must be a valid non-negative amount")
        else:
            try:
                decimal_amount = Decimal(str(amount))
                if not decimal_amount.is_finite() or decimal_amount < 0:
                    errors.append(
                        "total_estimated must be a valid non-negative amount"
                    )
                elif decimal_amount.as_tuple().exponent < -2:
                    errors.append(
                        "total_estimated cannot have more than two decimal places"
                    )
            except (InvalidOperation, ValueError, TypeError):
                errors.append(
                    "total_estimated must be a valid non-negative amount"
                )

    return OutputValidationResult(
        is_valid=not errors,
        errors=tuple(errors),
    )
