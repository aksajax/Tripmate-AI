
"""Unit tests for TripService and transactional audit logging."""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.db.models.trip import Trip
from app.repositories.audit_repository import AuditRepository
from app.repositories.trip_repository import TripRepository
from app.services.trip_service import TripService


@pytest.fixture
def db() -> Mock:
    return Mock()


@pytest.fixture
def service_with_mocks(monkeypatch: pytest.MonkeyPatch, db: Mock):
    trip_repository = Mock(spec=TripRepository)
    audit_repository = Mock(spec=AuditRepository)

    def create_trip_record(trip: Trip) -> Trip:
        if trip.id is None:
            trip.id = uuid.uuid4()
        return trip

    trip_repository.create.side_effect = create_trip_record

    monkeypatch.setattr(
        "app.services.trip_service.TripRepository",
        lambda session: trip_repository,
    )
    monkeypatch.setattr(
        "app.services.trip_service.AuditRepository",
        lambda session: audit_repository,
    )

    service = TripService(db)

    return service, trip_repository, audit_repository


def valid_trip_data(user_id: uuid.UUID) -> dict:
    return {
        "user_id": user_id,
        "origin": " Bengaluru ",
        "destination": "Goa",
        "start_date": date(2027, 1, 10),
        "end_date": date(2027, 1, 15),
        "travelers": 2,
        "budget": Decimal("25000.00"),
        "currency": "INR",
        "travel_style": "balanced",
    }


def test_create_trip_records_audit_and_commits(
    db: Mock, service_with_mocks
) -> None:
    service, trip_repository, audit_repository = service_with_mocks
    user_id = uuid.uuid4()

    trip = service.create_trip(**valid_trip_data(user_id))

    assert isinstance(trip, Trip)
    assert trip.user_id == user_id
    assert trip.origin == "Bengaluru"
    assert trip.destination == "Goa"

    trip_repository.create.assert_called_once()
    audit_repository.record_event.assert_called_once()

    audit_kwargs = audit_repository.record_event.call_args.kwargs
    assert audit_kwargs["actor_user_id"] == user_id
    assert audit_kwargs["action"] == "trip.created"
    assert audit_kwargs["entity_type"] == "trip"
    assert audit_kwargs["entity_id"] == trip.id
    assert audit_kwargs["details"]["origin"] == "Bengaluru"
    assert audit_kwargs["details"]["destination"] == "Goa"

    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(trip)
    db.rollback.assert_not_called()


def test_create_trip_rolls_back_when_audit_recording_fails(
    db: Mock, service_with_mocks
) -> None:
    service, trip_repository, audit_repository = service_with_mocks
    audit_repository.record_event.side_effect = RuntimeError("Audit storage failed")

    with pytest.raises(RuntimeError, match="Audit storage failed"):
        service.create_trip(**valid_trip_data(uuid.uuid4()))

    trip_repository.create.assert_called_once()
    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()


def test_create_trip_rolls_back_when_commit_fails(
    db: Mock, service_with_mocks
) -> None:
    service, trip_repository, audit_repository = service_with_mocks
    db.commit.side_effect = RuntimeError("Database commit failed")

    with pytest.raises(RuntimeError, match="Database commit failed"):
        service.create_trip(**valid_trip_data(uuid.uuid4()))

    trip_repository.create.assert_called_once()
    audit_repository.record_event.assert_called_once()
    db.rollback.assert_called_once_with()


def test_create_trip_does_not_persist_when_validation_fails(
    db: Mock, service_with_mocks
) -> None:
    service, trip_repository, audit_repository = service_with_mocks
    data = valid_trip_data(uuid.uuid4())
    data["destination"] = "Bengaluru"

    with pytest.raises(ValueError, match="Origin and destination must be different"):
        service.create_trip(**data)

    trip_repository.create.assert_not_called()
    audit_repository.record_event.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_list_user_trips_delegates_pagination(
    service_with_mocks,
) -> None:
    service, trip_repository, _ = service_with_mocks
    user_id = uuid.uuid4()
    expected_trips = [Mock(spec=Trip)]
    trip_repository.list_by_user.return_value = expected_trips

    result = service.list_user_trips(user_id, limit=10, offset=5)

    assert result == expected_trips
    trip_repository.list_by_user.assert_called_once_with(
        user_id,
        limit=10,
        offset=5,
    )
