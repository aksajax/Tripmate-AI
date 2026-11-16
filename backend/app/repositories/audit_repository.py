
"""Repository for append-only TripMate AI audit events."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit import AuditEvent


class AuditRepository:
    """Persist audit events within the caller's database transaction."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def record_event(
        self,
        *,
        action: str,
        entity_type: str,
        actor_user_id: uuid.UUID | None = None,
        entity_id: str | uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> AuditEvent:
        """Add an audit event and flush it without committing the transaction.

        The caller controls commit and rollback so the audit record can be
        saved atomically with the business operation it describes.
        """
        normalized_action = action.strip()
        normalized_entity_type = entity_type.strip()

        if not normalized_action:
            raise ValueError("action cannot be blank")
        if len(normalized_action) > 100:
            raise ValueError("action cannot exceed 100 characters")

        if not normalized_entity_type:
            raise ValueError("entity_type cannot be blank")
        if len(normalized_entity_type) > 100:
            raise ValueError("entity_type cannot exceed 100 characters")

        normalized_entity_id = (
            str(entity_id) if entity_id is not None else None
        )
        if normalized_entity_id is not None and len(normalized_entity_id) > 100:
            raise ValueError("entity_id cannot exceed 100 characters")

        normalized_correlation_id = (
            correlation_id.strip() if correlation_id is not None else None
        )
        if normalized_correlation_id == "":
            normalized_correlation_id = None
        if (
            normalized_correlation_id is not None
            and len(normalized_correlation_id) > 100
        ):
            raise ValueError("correlation_id cannot exceed 100 characters")

        if details is not None and not isinstance(details, dict):
            raise ValueError("details must be a dictionary")

        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=normalized_action,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            details=dict(details) if details is not None else {},
            correlation_id=normalized_correlation_id,
        )

        self.db.add(event)
        self.db.flush()
        return event
