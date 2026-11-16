
"""Unit tests for persistent idempotency record storage."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.db.models.idempotency import IdempotencyRecord
from app.repositories.idempotency_repository import IdempotencyRepository


@pytest.fixture
def db():
    """Provide a mocked SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def repository(db):
    """Create the repository under test."""
    return IdempotencyRepository(db)


@pytest.fixture
def valid_record_data():
    """Provide valid idempotency record fields."""
    return {
        "user_id": uuid4(),
        "key": "trip-create-test-001",
        "request_hash": "a" * 64,
        "response_status": 201,
        "response_body": {
            "id": str(uuid4()),
            "origin": "Bengaluru",
            "destination": "Goa",
        },
    }


def test_get_by_user_and_key_returns_existing_record(
    db, repository
):
    """Return a record when the key already exists."""
    user_id = uuid4()
    record = MagicMock(spec=IdempotencyRecord)

    db.execute.return_value.scalar_one_or_none.return_value = record

    result = repository.get_by_user_and_key(
        user_id=user_id,
        key="trip-create-test-001",
    )

    assert result is record
    db.execute.assert_called_once()


def test_get_by_user_and_key_returns_none_when_missing(
    db, repository
):
    """Return None when no record matches."""
    db.execute.return_value.scalar_one_or_none.return_value = None

    result = repository.get_by_user_and_key(
        user_id=uuid4(),
        key="trip-create-missing",
    )

    assert result is None


def test_create_persists_valid_record(
    db, repository, valid_record_data
):
    """Add, flush, and refresh a valid record without committing."""
    result = repository.create(**valid_record_data)

    assert isinstance(result, IdempotencyRecord)
    assert result.user_id == valid_record_data["user_id"]
    assert result.key == valid_record_data["key"]
    assert result.request_hash == valid_record_data["request_hash"]
    assert result.response_status == 201
    assert result.response_body == valid_record_data["response_body"]

    db.add.assert_called_once_with(result)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(result)
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key", ""),
        ("key", " " * 3),
        ("key", "x" * 129),
        ("request_hash", "abc"),
        ("request_hash", "g" * 64),
        ("response_status", 99),
        ("response_status", 600),
        ("response_status", True),
        ("response_body", []),
        ("response_body", None),
    ],
)
def test_create_rejects_invalid_record_data(
    db, repository, valid_record_data, field, value
):
    """Reject malformed idempotency records before database writes."""
    data = {**valid_record_data, field: value}

    with pytest.raises(ValueError):
        repository.create(**data)

    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_create_rejects_non_integer_response_status(
    db, repository, valid_record_data
):
    """Reject response status values that are not integers."""
    data = {**valid_record_data, "response_status": "201"}

    with pytest.raises(ValueError):
        repository.create(**data)

    db.add.assert_not_called()
    db.flush.assert_not_called()
