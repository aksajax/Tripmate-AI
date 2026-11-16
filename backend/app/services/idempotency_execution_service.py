
"""Atomic PostgreSQL-backed idempotency operations."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models.idempotency import IdempotencyRecord
from app.services.idempotency_service import IdempotencyService


class IdempotencyConflictError(ValueError):
    """Raised when a key is reused with different request data."""


class IdempotencyExecutionService:
    """Manage idempotency records within caller-controlled transactions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.hashing = IdempotencyService(repository=None)

    def find_existing(
        self,
        *,
        user_id: uuid.UUID,
        key: str,
        payload: dict[str, Any],
    ) -> IdempotencyRecord | None:
        """Find a previous response and reject mismatched request data."""
        normalized_key = self.hashing.validate_key(key)
        request_hash = self.hashing.hash_request(payload)

        record = self.db.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.key == normalized_key,
            )
        ).scalar_one_or_none()

        if record is not None:
            self._ensure_same_request(record, request_hash)

        return record

    def store_response(
        self,
        *,
        user_id: uuid.UUID,
        key: str,
        payload: dict[str, Any],
        response_status: int,
        response_body: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        """Store a response atomically.

        Returns (record, True) if this call inserted the record.
        Returns (existing_record, False) if another request already inserted it.

        The caller must commit or roll back the surrounding transaction.
        """
        normalized_key = self.hashing.validate_key(key)
        request_hash = self.hashing.hash_request(payload)

        if (
            not isinstance(response_status, int)
            or isinstance(response_status, bool)
            or not 100 <= response_status <= 599
        ):
            raise ValueError("Response status must be an integer between 100 and 599")

        if not isinstance(response_body, dict):
            raise ValueError("Response body must be a dictionary")

        statement = (
            insert(IdempotencyRecord)
            .values(
                user_id=user_id,
                key=normalized_key,
                request_hash=request_hash,
                response_status=response_status,
                response_body=dict(response_body),
            )
            .on_conflict_do_nothing(
                constraint="uq_idempotency_records_user_key"
            )
            .returning(IdempotencyRecord.id)
        )

        inserted_id = self.db.execute(statement).scalar_one_or_none()

        if inserted_id is not None:
            record = self.db.execute(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.id == inserted_id
                )
            ).scalar_one()
            return record, True

        # PostgreSQL waits for a concurrent insert to resolve before
        # returning from ON CONFLICT DO NOTHING.
        existing = self.db.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.key == normalized_key,
            )
        ).scalar_one_or_none()

        if existing is None:
            raise RuntimeError(
                "Idempotency conflict occurred, but no existing record was found"
            )

        self._ensure_same_request(existing, request_hash)
        return existing, False

    def _ensure_same_request(
        self,
        record: IdempotencyRecord,
        request_hash: str,
    ) -> None:
        """Reject reuse of a key for different request content."""
        try:
            self.hashing.ensure_same_request(record, request_hash)
        except ValueError as exc:
            raise IdempotencyConflictError(str(exc)) from exc
