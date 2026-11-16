
"""Unit tests for TripMate AI access-token utilities."""

import pytest

from app.core.tokens import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
)

TEST_SECRET = "unit-test-secret-key-with-at-least-32-bytes"


def test_create_and_decode_access_token() -> None:
    token = create_access_token(
        "test-user-id",
        TEST_SECRET,
        now=1000,
    )

    claims = decode_access_token(
        token,
        TEST_SECRET,
        now=1001,
    )

    assert claims["sub"] == "test-user-id"
    assert claims["iat"] == 1000
    assert claims["exp"] == 1900


def test_token_has_three_parts() -> None:
    token = create_access_token("user-123", TEST_SECRET, now=1000)

    assert len(token.split(".")) == 3


def test_tampered_token_is_rejected() -> None:
    token = create_access_token("user-123", TEST_SECRET, now=1000)
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    tampered_token = ".".join(parts)

    with pytest.raises(TokenValidationError):
        decode_access_token(tampered_token, TEST_SECRET, now=1001)


def test_wrong_secret_is_rejected() -> None:
    token = create_access_token("user-123", TEST_SECRET, now=1000)

    with pytest.raises(TokenValidationError):
        decode_access_token(
            token,
            "different-test-secret-with-at-least-32-bytes",
            now=1001,
        )


def test_expired_token_is_rejected() -> None:
    token = create_access_token("user-123", TEST_SECRET, now=1000)

    with pytest.raises(TokenValidationError, match="expired"):
        decode_access_token(token, TEST_SECRET, now=1900)


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(TokenValidationError, match="format"):
        decode_access_token("not-a-valid-token", TEST_SECRET, now=1000)


def test_short_secret_is_rejected_when_creating_token() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        create_access_token("user-123", "short-secret", now=1000)


def test_short_secret_is_rejected_when_decoding_token() -> None:
    token = create_access_token("user-123", TEST_SECRET, now=1000)

    with pytest.raises(TokenValidationError, match="configuration"):
        decode_access_token(token, "short-secret", now=1001)


def test_empty_subject_is_rejected() -> None:
    with pytest.raises(ValueError, match="subject"):
        create_access_token(" ", TEST_SECRET, now=1000)


def test_invalid_expiration_is_rejected() -> None:
    with pytest.raises(ValueError, match="expires_in_seconds"):
        create_access_token(
            "user-123",
            TEST_SECRET,
            expires_in_seconds=0,
            now=1000,
        )


def test_future_issued_token_is_rejected() -> None:
    token = create_access_token("user-123", TEST_SECRET, now=2000)

    with pytest.raises(TokenValidationError, match="future"):
        decode_access_token(token, TEST_SECRET, now=1000)
