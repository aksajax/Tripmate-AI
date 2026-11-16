
"""Unit tests for the TripMate AI user repository."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repository import UserRepository


@pytest.fixture
def db():
    """Provide a mocked SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def repository(db):
    """Create a repository using the mocked session."""
    return UserRepository(db)


def test_create_user_flushes_and_refreshes(repository, db):
    """Add a new user without committing the transaction."""
    user = repository.create(
        email="Traveler@example.com",
        display_name="Traveler",
        password_hash="secure-test-hash",
    )

    assert user.email == "traveler@example.com"
    assert user.display_name == "Traveler"
    assert user.password_hash == "secure-test-hash"
    assert user.is_active is True
    assert user.is_superuser is False

    db.add.assert_called_once_with(user)
    db.flush.assert_called_once_with()
    db.refresh.assert_called_once_with(user)
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_create_user_rolls_back_on_duplicate_email(repository, db):
    """Convert a database uniqueness failure into a safe error."""
    db.flush.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("duplicate key"),
    )

    with pytest.raises(ValueError, match="already exists"):
        repository.create(
            email="traveler@example.com",
            display_name="Traveler",
            password_hash="secure-test-hash",
        )

    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_create_user_rolls_back_on_unexpected_error(repository, db):
    """Roll back the transaction if flushing fails."""
    db.flush.side_effect = RuntimeError("database failure")

    with pytest.raises(RuntimeError, match="database failure"):
        repository.create(
            email="traveler@example.com",
            display_name="Traveler",
            password_hash="secure-test-hash",
        )

    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_get_by_email_returns_matching_user(repository, db):
    """Return a user found by normalized email."""
    expected_user = SimpleNamespace(email="traveler@example.com")
    db.execute.return_value.scalar_one_or_none.return_value = expected_user

    result = repository.get_by_email(" Traveler@Example.com ")

    assert result is expected_user
    db.execute.assert_called_once()


def test_get_by_email_returns_none_when_missing(repository, db):
    """Return None when no account matches the email."""
    db.execute.return_value.scalar_one_or_none.return_value = None

    result = repository.get_by_email("missing@example.com")

    assert result is None


def test_get_by_id_returns_matching_user(repository, db):
    """Look up a user by UUID."""
    user_id = uuid.uuid4()
    expected_user = SimpleNamespace(id=user_id)
    db.execute.return_value.scalar_one_or_none.return_value = expected_user

    result = repository.get_by_id(user_id)

    assert result is expected_user


def test_email_exists_returns_true(repository, db):
    """Report when an email is already registered."""
    db.execute.return_value.scalar_one_or_none.return_value = "user-id"

    assert repository.email_exists("Traveler@Example.com") is True


def test_email_exists_returns_false(repository, db):
    """Report when an email is not registered."""
    db.execute.return_value.scalar_one_or_none.return_value = None

    assert repository.email_exists("missing@example.com") is False
