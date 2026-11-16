
"""Unit tests for TripMate AI authentication schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)


def test_valid_user_registration() -> None:
    user = UserRegister(
        email="traveler@example.com",
        display_name="Traveler",
        password="TripMateDemo!2026",
    )

    assert user.email == "traveler@example.com"
    assert user.display_name == "Traveler"


def test_registration_normalizes_email() -> None:
    user = UserRegister(
        email="Traveler@Example.com",
        display_name="Traveler",
        password="TripMateDemo!2026",
    )

    assert user.email == "traveler@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "invalid-email",
        "traveler@",
        "@example.com",
        "traveler@example",
    ],
)
def test_registration_rejects_invalid_email(email: str) -> None:
    with pytest.raises(ValidationError):
        UserRegister(
            email=email,
            display_name="Traveler",
            password="TripMateDemo!2026",
        )


def test_registration_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserRegister(
            email="traveler@example.com",
            display_name="Traveler",
            password="short",
        )


def test_registration_rejects_blank_display_name() -> None:
    with pytest.raises(ValidationError):
        UserRegister(
            email="traveler@example.com",
            display_name="   ",
            password="TripMateDemo!2026",
        )


def test_registration_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        UserRegister(
            email="traveler@example.com",
            display_name="Traveler",
            password="TripMateDemo!2026",
            is_superuser=True,
        )


def test_login_normalizes_email() -> None:
    login = UserLogin(
        email="  Traveler@Example.com  ",
        password="TripMateDemo!2026",
    )

    assert login.email == "traveler@example.com"


def test_login_rejects_missing_password() -> None:
    with pytest.raises(ValidationError):
        UserLogin(email="traveler@example.com", password="")


def test_token_response_defaults_to_bearer() -> None:
    token = TokenResponse(
        access_token="example-token",
        expires_in=900,
    )

    assert token.token_type == "bearer"
    assert token.expires_in == 900


def test_token_response_rejects_non_positive_expiration() -> None:
    with pytest.raises(ValidationError):
        TokenResponse(
            access_token="example-token",
            expires_in=0,
        )


def test_user_response_excludes_password_hash() -> None:
    user = UserResponse(
        id=uuid.uuid4(),
        email="traveler@example.com",
        display_name="Traveler",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    response_data = user.model_dump()

    assert "password_hash" not in response_data
    assert "password" not in response_data
