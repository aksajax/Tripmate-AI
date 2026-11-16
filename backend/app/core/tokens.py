
"""Signed access-token utilities for TripMate AI."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any


TOKEN_ALGORITHM = "HS256"
TOKEN_TYPE = "JWT"
DEFAULT_EXPIRES_IN_SECONDS = 900


class TokenValidationError(ValueError):
    """Raised when an access token is invalid or expired."""


def _base64url_encode(value: bytes) -> str:
    """Encode bytes using URL-safe Base64 without padding."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    """Decode URL-safe Base64 while validating its format."""
    allowed = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789-_"
    )
    if not value or any(character not in allowed for character in value):
        raise TokenValidationError("Invalid token encoding")

    padded = value + "=" * (-len(value) % 4)

    try:
        return base64.b64decode(
            padded.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, UnicodeError):
        raise TokenValidationError("Invalid token encoding") from None


def create_access_token(
    subject: str,
    secret_key: str,
    *,
    expires_in_seconds: int = DEFAULT_EXPIRES_IN_SECONDS,
    now: int | None = None,
) -> str:
    """Create an HS256-signed access token."""
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("subject must be a non-empty string")

    if (
        not isinstance(secret_key, str)
        or len(secret_key.encode("utf-8")) < 32
    ):
        raise ValueError("secret_key must contain at least 32 bytes")

    if (
        isinstance(expires_in_seconds, bool)
        or not isinstance(expires_in_seconds, int)
        or not 1 <= expires_in_seconds <= 86400
    ):
        raise ValueError("expires_in_seconds must be between 1 and 86400")

    issued_at = int(time.time()) if now is None else now
    if isinstance(issued_at, bool) or not isinstance(issued_at, int):
        raise ValueError("now must be an integer timestamp")

    header = {"alg": TOKEN_ALGORITHM, "typ": TOKEN_TYPE}
    payload = {
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + expires_in_seconds,
    }

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return (
        f"{encoded_header}.{encoded_payload}."
        f"{_base64url_encode(signature)}"
    )


def decode_access_token(
    token: str,
    secret_key: str,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Verify a token's signature, format, and expiration."""
    if not isinstance(token, str) or not isinstance(secret_key, str):
        raise TokenValidationError("Invalid token")

    if len(secret_key.encode("utf-8")) < 32:
        raise TokenValidationError("Invalid token configuration")

    parts = token.split(".")
    if len(parts) != 3:
        raise TokenValidationError("Invalid token format")

    encoded_header, encoded_payload, encoded_signature = parts

    try:
        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
        signature = _base64url_decode(encoded_signature)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise TokenValidationError("Invalid token contents") from None

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise TokenValidationError("Invalid token contents")

    if header != {"alg": TOKEN_ALGORITHM, "typ": TOKEN_TYPE}:
        raise TokenValidationError("Unsupported token header")

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(signature, expected_signature):
        raise TokenValidationError("Invalid token signature")

    subject = payload.get("sub")
    issued_at = payload.get("iat")
    expires_at = payload.get("exp")

    if not isinstance(subject, str) or not subject.strip():
        raise TokenValidationError("Invalid token subject")

    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, int)
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, int)
    ):
        raise TokenValidationError("Invalid token timestamps")

    current_time = int(time.time()) if now is None else now
    if isinstance(current_time, bool) or not isinstance(current_time, int):
        raise TokenValidationError("Invalid current timestamp")

    if issued_at > current_time:
        raise TokenValidationError("Token issued in the future")

    if expires_at <= current_time:
        raise TokenValidationError("Token has expired")

    if expires_at <= issued_at or expires_at - issued_at > 86400:
        raise TokenValidationError("Invalid token lifetime")

    return payload
