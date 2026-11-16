
"""Service utilities for safe API idempotency."""

import hashlib
import json
import re
import uuid
from typing import Any

from app.db.models.idempotency import IdempotencyRecord
from app.repositories.idempotency_repository import IdempotencyRepository


class IdempotencyService:
    """Validate idempotency keys and compare request fingerprints."""

    KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

    def __init__(self, repository: IdempotencyRepository) -> None:
        self.repository = repository

    @classmethod
    def validate_key(cls, key: str) -> str:
        """Validate a client-provided idempotency key."""
        if not isinstance(key, str):
            raise ValueError("Idempotency key must be a string")

        normalized = key.strip()

        if not cls.KEY_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Idempotency key must contain 1-128 letters, digits, "
                "periods, underscores, colons, or hyphens"
            )

        return normalized

    @staticmethod
    def hash_request(payload: dict[str, Any]) -> str:
        """Return a deterministic SHA-256 hash for a JSON-compatible payload."""
        if not isinstance(payload, dict):
            raise ValueError("Request payload must be a dictionary")

        try:
            canonical_json = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Request payload must be valid JSON data") from exc

        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def get_existing(
        self,
        user_id: uuid.UUID,
        key: str,
    ) -> IdempotencyRecord | None:
        """Find a previous request for the same user and key."""
        normalized_key = self.validate_key(key)
        return self.repository.get_by_user_and_key(user_id, normalized_key)

    @staticmethod
    def ensure_same_request(
        record: IdempotencyRecord,
        request_hash: str,
    ) -> None:
        """Reject a key reused for a different request."""
        if record.request_hash != request_hash:
            raise ValueError(
                "Idempotency key has already been used with a different request"
            )
