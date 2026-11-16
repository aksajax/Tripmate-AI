
"""Database repository for persistent API idempotency records."""
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    """Read and write idempotency records within a caller-managed transaction."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_and_key(
        self,
        user_id: uuid.UUID,
        key: str,
    ) -> IdempotencyRecord | None:
        """Return the record associated with a user's idempotency key."""
        statement = select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.key == key,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def create(
        self,
        *,
        user_id: uuid.UUID,
        key: str,
        request_hash: str,
        response_status: int,
        response_body: dict,
    ) -> IdempotencyRecord:
        """Stage a new idempotency record without committing."""
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Idempotency key must not be blank")

        if len(key) > 128:
            raise ValueError("Idempotency key must not exceed 128 characters")

        if (
            not isinstance(request_hash, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", request_hash) is None
        ):
            raise ValueError(
                "request_hash must be a 64-character hexadecimal SHA-256 hash"
            )

        if not isinstance(response_status, int) or isinstance(response_status, bool):
            raise ValueError("Response status must be an integer")

        if not 100 <= response_status <= 599:
            raise ValueError("Response status must be between 100 and 599")

        if not isinstance(response_body, dict):
            raise ValueError("Response body must be a dictionary")

        record = IdempotencyRecord(
            user_id=user_id,
            key=key.strip(),
            request_hash=request_hash,
            response_status=response_status,
            response_body=dict(response_body),
        )

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record
