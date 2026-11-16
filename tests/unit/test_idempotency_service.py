
"""Unit tests for the idempotency service."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.idempotency_service import IdempotencyService


@pytest.fixture
def repository():
    return MagicMock()


@pytest.fixture
def service(repository):
    return IdempotencyService(repository)


def test_validate_key_accepts_valid_key(service):
    assert service.validate_key("trip-create:request_123") == (
        "trip-create:request_123"
    )


def test_validate_key_trims_surrounding_whitespace(service):
    assert service.validate_key("  request-123  ") == "request-123"


@pytest.mark.parametrize(
    "key",
    [
        "",
        "   ",
        "key with spaces",
        "key/with/slashes",
        "key" * 50,
        None,
    ],
)
def test_validate_key_rejects_invalid_key(service, key):
    with pytest.raises(ValueError, match="Idempotency key"):
        service.validate_key(key)


def test_hash_request_is_deterministic(service):
    first = service.hash_request({"origin": "Bengaluru", "destination": "Goa"})
    second = service.hash_request({"destination": "Goa", "origin": "Bengaluru"})

    assert first == second
    assert len(first) == 64


def test_hash_request_changes_when_payload_changes(service):
    first = service.hash_request({"origin": "Bengaluru", "destination": "Goa"})
    second = service.hash_request({"origin": "Bengaluru", "destination": "Pune"})

    assert first != second


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "not a dictionary",
        {"amount": float("nan")},
        {"amount": float("inf")},
        {"value": object()},
    ],
)
def test_hash_request_rejects_invalid_payload(service, payload):
    with pytest.raises(ValueError, match="Request payload"):
        service.hash_request(payload)


def test_get_existing_normalizes_key_and_uses_user(repository, service):
    user_id = uuid.uuid4()
    expected = SimpleNamespace(key="request-123")
    repository.get_by_user_and_key.return_value = expected

    result = service.get_existing(user_id, " request-123 ")

    assert result is expected
    repository.get_by_user_and_key.assert_called_once_with(
        user_id,
        "request-123",
    )


def test_ensure_same_request_accepts_matching_hash(service):
    record = SimpleNamespace(request_hash="a" * 64)

    service.ensure_same_request(record, "a" * 64)


def test_ensure_same_request_rejects_different_hash(service):
    record = SimpleNamespace(request_hash="a" * 64)

    with pytest.raises(ValueError, match="different request"):
        service.ensure_same_request(record, "b" * 64)
