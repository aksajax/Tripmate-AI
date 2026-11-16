
"""Unit tests for TripMate AI password security utilities."""

import pytest

from app.core.security import hash_password, verify_password


def test_hash_password_does_not_store_plaintext() -> None:
    password = "TripMateDemo!2026"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("pbkdf2_sha256$")


def test_correct_password_verifies() -> None:
    password = "TripMateDemo!2026"
    hashed = hash_password(password)

    assert verify_password(password, hashed)


def test_incorrect_password_is_rejected() -> None:
    hashed = hash_password("TripMateDemo!2026")

    assert not verify_password("WrongPassword!2026", hashed)


def test_same_password_produces_different_hashes() -> None:
    password = "TripMateDemo!2026"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        hash_password("short")


def test_non_string_password_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        hash_password(None)  # type: ignore[arg-type]


def test_password_over_maximum_length_is_rejected() -> None:
    with pytest.raises(ValueError, match="too long"):
        hash_password("a" * 1025)


@pytest.mark.parametrize(
    "stored_hash",
    [
        "",
        "invalid-hash",
        "unknown$600000$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$invalid$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$1$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$600000$%%%$aGFzaA==",
    ],
)
def test_malformed_hash_is_rejected(stored_hash: str) -> None:
    assert not verify_password("TripMateDemo!2026", stored_hash)


def test_non_string_values_are_rejected_during_verification() -> None:
    assert not verify_password(None, "invalid")  # type: ignore[arg-type]
    assert not verify_password("password", None)  # type: ignore[arg-type]
