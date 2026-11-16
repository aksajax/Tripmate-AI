
"""Password security utilities for TripMate AI."""

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16
HASH_BYTES = 32


def hash_password(password: str) -> str:
    """Return a salted password hash suitable for database storage."""
    if not isinstance(password, str):
        raise TypeError("password must be a string")

    if len(password) < 8:
        raise ValueError("password must contain at least 8 characters")

    if len(password) > 1024:
        raise ValueError("password is too long")

    salt = secrets.token_bytes(SALT_BYTES)

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=HASH_BYTES,
    )

    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_hash = base64.urlsafe_b64encode(derived_key).decode("ascii")

    return (
        f"{ALGORITHM}${ITERATIONS}"
        f"${encoded_salt}${encoded_hash}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a previously stored password hash."""
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False

    try:
        algorithm, iterations_text, encoded_salt, encoded_hash = (
            stored_hash.split("$")
        )

        if algorithm != ALGORITHM:
            return False

        iterations = int(iterations_text)

        # Reject malformed or unexpectedly expensive hash parameters.
        if not 100_000 <= iterations <= 1_000_000:
            return False

        salt = base64.b64decode(
            encoded_salt.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
        expected_hash = base64.b64decode(
            encoded_hash.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )

        if len(salt) != SALT_BYTES or len(expected_hash) != HASH_BYTES:
            return False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected_hash),
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError, UnicodeError):
        return False
    