
"""Unit tests for the audit repository."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.db.models.audit import AuditEvent
from app.repositories.audit_repository import AuditRepository


@pytest.fixture
def db() -> Mock:
    return Mock()


@pytest.fixture
def repository(db: Mock) -> AuditRepository:
    return AuditRepository(db)


def test_record_event_creates_and_flushes_event(
    repository: AuditRepository, db: Mock
) -> None:
    actor_id = uuid4()
    entity_id = uuid4()

    event = repository.record_event(
        actor_user_id=actor_id,
        action="trip.created",
        entity_type="trip",
        entity_id=entity_id,
        details={"origin": "Bengaluru", "destination": "Goa"},
        correlation_id="request-123",
    )

    assert isinstance(event, AuditEvent)
    assert event.actor_user_id == actor_id
    assert event.action == "trip.created"
    assert event.entity_type == "trip"
    assert event.entity_id == str(entity_id)
    assert event.details == {
        "origin": "Bengaluru",
        "destination": "Goa",
    }
    assert event.correlation_id == "request-123"

    db.add.assert_called_once_with(event)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()


def test_record_event_supports_anonymous_actor(
    repository: AuditRepository,
) -> None:
    event = repository.record_event(
        action="user.registered",
        entity_type="user",
    )

    assert event.actor_user_id is None
    assert event.entity_id is None
    assert event.details == {}
    assert event.correlation_id is None


@pytest.mark.parametrize("action", ["", " ", "\t"])
def test_record_event_rejects_blank_action(
    repository: AuditRepository, action: str
) -> None:
    with pytest.raises(ValueError, match="action cannot be blank"):
        repository.record_event(action=action, entity_type="trip")


def test_record_event_rejects_long_action(
    repository: AuditRepository,
) -> None:
    with pytest.raises(ValueError, match="action cannot exceed 100 characters"):
        repository.record_event(action="a" * 101, entity_type="trip")


@pytest.mark.parametrize("entity_type", ["", " ", "\t"])
def test_record_event_rejects_blank_entity_type(
    repository: AuditRepository, entity_type: str
) -> None:
    with pytest.raises(ValueError, match="entity_type cannot be blank"):
        repository.record_event(action="trip.created", entity_type=entity_type)


def test_record_event_rejects_long_entity_type(
    repository: AuditRepository,
) -> None:
    with pytest.raises(
        ValueError, match="entity_type cannot exceed 100 characters"
    ):
        repository.record_event(action="trip.created", entity_type="x" * 101)


def test_record_event_rejects_long_entity_id(
    repository: AuditRepository,
) -> None:
    with pytest.raises(ValueError, match="entity_id cannot exceed 100 characters"):
        repository.record_event(
            action="trip.created",
            entity_type="trip",
            entity_id="x" * 101,
        )


def test_record_event_rejects_long_correlation_id(
    repository: AuditRepository,
) -> None:
    with pytest.raises(
        ValueError, match="correlation_id cannot exceed 100 characters"
    ):
        repository.record_event(
            action="trip.created",
            entity_type="trip",
            correlation_id="x" * 101,
        )


def test_record_event_rejects_non_dictionary_details(
    repository: AuditRepository,
) -> None:
    with pytest.raises(ValueError, match="details must be a dictionary"):
        repository.record_event(
            action="trip.created",
            entity_type="trip",
            details=["not", "a", "dictionary"],  # type: ignore[arg-type]
        )


def test_record_event_normalizes_strings_and_copies_details(
    repository: AuditRepository,
) -> None:
    details = {"source": "api"}

    event = repository.record_event(
        action=" trip.created ",
        entity_type=" trip ",
        details=details,
        correlation_id=" request-456 ",
    )

    details["extra"] = "not copied"

    assert event.action == "trip.created"
    assert event.entity_type == "trip"
    assert event.correlation_id == "request-456"
    assert event.details == {"source": "api"}


def test_record_event_does_not_add_event_when_action_is_invalid(
    repository: AuditRepository, db: Mock
) -> None:
    with pytest.raises(ValueError):
        repository.record_event(action=" ", entity_type="trip")

    db.add.assert_not_called()
    db.flush.assert_not_called()
