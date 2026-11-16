
"""Input validation guardrails for TripMate AI."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InputValidationResult:
    """Result of validating user-provided text."""

    is_valid: bool
    normalized_text: str
    errors: tuple[str, ...]


# These patterns flag common attempts to override the assistant's instructions.
# Detection is advisory: legitimate travel text may occasionally match a pattern.
_SUSPICIOUS_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.I),
    re.compile(r"\b(reveal|print|show)\s+(the\s+)?system prompt\b", re.I),
    re.compile(r"\bdeveloper message\b", re.I),
    re.compile(r"<\s*system\s*>", re.I),
)

DEFAULT_MAX_LENGTH = 5000


def validate_user_text(
    value: str,
    *,
    field_name: str = "text",
    max_length: int = DEFAULT_MAX_LENGTH,
    reject_suspicious_patterns: bool = True,
) -> InputValidationResult:
    """Validate and normalize user-provided text without executing it."""
    errors: list[str] = []

    if not isinstance(value, str):
        return InputValidationResult(
            is_valid=False,
            normalized_text="",
            errors=(f"{field_name} must be a string",),
        )

    if max_length < 1:
        raise ValueError("max_length must be at least 1")

    normalized = value.strip()

    if not normalized:
        errors.append(f"{field_name} cannot be empty")

    if len(normalized) > max_length:
        errors.append(
            f"{field_name} exceeds the maximum length of {max_length}"
        )

    if reject_suspicious_patterns:
        if any(pattern.search(normalized) for pattern in _SUSPICIOUS_PATTERNS):
            errors.append(
                f"{field_name} contains a potentially unsafe instruction pattern"
            )

    return InputValidationResult(
        is_valid=not errors,
        normalized_text=normalized,
        errors=tuple(errors),
    )
