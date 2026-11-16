
"""Unit tests for atomic idempotency execution."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models.idempotency import IdempotencyRecord
from app.services.idempotency_execution_service import (
    IdempotencyConflictError,
    IdempotencyExecutionService,
)


@pytest.fixture
def db():
    """Provide a mocked SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def service(db):
    """Create the service under test."""
    return IdempotencyExecutionService(db)


@pytest.fixture
def request_data():
    """Provide a valid request and response."""
    return {
        "user_id": uuid4(),
        "key": "trip-create-unit-001",
        "payload": {
            "origin": "Bengaluru",
            "destination": "Goa",
            "travelers": 2,
        },
        "response_status": 201,
        "response_body": {
            "id": str(uuid4()),
            "origin": "Bengaluru",
            "destination": "Goa",
        },
    }


def test_find_existing_returns_none_when_key_is_new(
    db, service, request_data
):
    """Return None when the key is not stored."""
    db.execute.return_value.scalar_one_or_none.return_value = None

    result = service.find_existing(
        user_id=request_data["user_id"],
        key=request_data["key"],
        payload=request_data["payload"],
    )

    assert result is None
    db.execute.assert_called_once()


def test_find_existing_returns_matching_record(
    db, service, request_data
):
    """Return a saved record when its request hash matches."""
    request_hash = service.hashing.hash_request(request_data["payload"])
    record = MagicMock(spec=IdempotencyRecord)
    record.request_hash = request_hash

    db.execute.return_value.scalar_one_or_none.return_value = record

    result = service.find_existing(
        user_id=request_data["user_id"],
        key=request_data["key"],
        payload=request_data["payload"],
    )

    assert result is record


def test_find_existing_rejects_different_payload(
    db, service, request_data
):
    """Reject reuse of a key for different request data."""
    record = MagicMock(spec=IdempotencyRecord)
    record.request_hash = "a" * 64
    db.execute.return_value.scalar_one_or_none.return_value = record

    with pytest.raises(IdempotencyConflictError):
        service.find_existing(
            user_id=request_data["user_id"],
            key=request_data["key"],
            payload=request_data["payload"],
        )



def test_store_response_returns_inserted_record(
    db, service, request_data
):
    """Return the new record when the insert wins."""
    record_id = uuid4()
    record = MagicMock(spec=IdempotencyRecord)

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = record_id

    select_result = MagicMock()
    select_result.scalar_one.return_value = record
    select_result.scalar_one_or_none.return_value = record

    db.execute.side_effect = [insert_result, select_result]

    result, inserted = service.store_response(
        user_id=request_data["user_id"],
        key=request_data["key"],
        payload=request_data["payload"],
        response_status=request_data["response_status"],
        response_body=request_data["response_body"],
    )

    assert result is record
    assert inserted is True
    db.execute.assert_called()
    db.commit.assert_not_called()




def test_store_response_reuses_existing_record_after_conflict(
    db, service, request_data
):
    """Return the existing row when another request inserted the key."""
    record = MagicMock(spec=IdempotencyRecord)
    record.request_hash = service.hashing.hash_request(
        request_data["payload"]
    )

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = None

    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = record

    db.execute.side_effect = [insert_result, select_result]

    result, inserted = service.store_response(
        user_id=request_data["user_id"],
        key=request_data["key"],
        payload=request_data["payload"],
        response_status=request_data["response_status"],
        response_body=request_data["response_body"],
    )

    assert result is record
    assert inserted is False
    db.commit.assert_not_called()




def test_store_response_rejects_key_reused_for_different_payload(
    db, service, request_data
):
    """Raise a conflict if a concurrent winner used another payload."""
    record = MagicMock(spec=IdempotencyRecord)
    record.request_hash = "a" * 64

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = None

    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = record

    db.execute.side_effect = [insert_result, select_result]

    with pytest.raises(IdempotencyConflictError):
        service.store_response(
            user_id=request_data["user_id"],
            key=request_data["key"],
            payload=request_data["payload"],
            response_status=request_data["response_status"],
            response_body=request_data["response_body"],
        )

    db.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key", ""),
        ("key", "invalid key with spaces"),
        ("response_status", 99),
        ("response_status", 600),
        ("response_status", True),
        ("response_body", []),
        ("response_body", None),
    ],
)
def test_store_response_rejects_invalid_inputs(
    db, service, request_data, field, value
):
    """Validate inputs before writing an idempotency record."""
    arguments = {
        "user_id": request_data["user_id"],
        "key": request_data["key"],
        "payload": request_data["payload"],
        "response_status": request_data["response_status"],
        "response_body": request_data["response_body"],
    }
    arguments[field] = value

    with pytest.raises(ValueError):
        service.store_response(**arguments)

    db.execute.assert_not_called()
