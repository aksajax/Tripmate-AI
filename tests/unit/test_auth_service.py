
"""Unit tests for TripMate AI authentication service."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.auth import UserLogin, UserRegister
from app.services.auth_service import AuthService


@pytest.fixture
def repository():
    """Provide a mocked user repository."""
    return MagicMock()


@pytest.fixture
def service(repository):
    """Provide an authentication service with a mocked repository."""
    return AuthService(repository)


@pytest.fixture
def registration_payload():
    """Provide valid registration data."""
    return UserRegister(
        email="traveler@example.com",
        display_name="Traveler",
        password="TripMateDemo!2026",
    )


@pytest.fixture
def login_payload():
    """Provide valid login data."""
    return UserLogin(
        email="traveler@example.com",
        password="TripMateDemo!2026",
    )


def test_register_hashes_password_and_creates_user(
    service,
    repository,
    registration_payload,
):
    """Hash the password, audit registration, and commit."""
    repository.email_exists.return_value = False
    expected_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="traveler@example.com",
    )
    repository.create.return_value = expected_user

    with patch(
        "app.services.auth_service.hash_password",
        return_value="secure-test-hash",
    ) as mock_hash:
        result = service.register(registration_payload)

    mock_hash.assert_called_once_with("TripMateDemo!2026")
    repository.create.assert_called_once_with(
        email="traveler@example.com",
        display_name="Traveler",
        password_hash="secure-test-hash",
    )

    assert result is expected_user
    repository.db.add.assert_called_once()
    repository.db.flush.assert_called()
    repository.db.commit.assert_called_once_with()
    repository.db.refresh.assert_called_once_with(expected_user)
    repository.db.rollback.assert_not_called()


def test_register_rejects_duplicate_email(
    service,
    repository,
    registration_payload,
):
    """Reject an existing email without hashing or creating a user."""
    repository.email_exists.return_value = True

    with patch("app.services.auth_service.hash_password") as mock_hash:
        with pytest.raises(ValueError, match="already exists"):
            service.register(registration_payload)

    mock_hash.assert_not_called()
    repository.create.assert_not_called()
    repository.db.commit.assert_not_called()


def test_register_rolls_back_when_audit_flush_fails(
    service,
    repository,
    registration_payload,
):
    """Roll back registration when recording the audit event fails."""
    repository.email_exists.return_value = False
    repository.create.return_value = SimpleNamespace(
        id=uuid.uuid4(),
        email="traveler@example.com",
    )
    repository.db.flush.side_effect = RuntimeError("audit storage failed")

    with patch(
        "app.services.auth_service.hash_password",
        return_value="secure-test-hash",
    ):
        with pytest.raises(RuntimeError, match="audit storage failed"):
            service.register(registration_payload)

    repository.db.commit.assert_not_called()
    repository.db.rollback.assert_called_once_with()


def test_authenticate_accepts_valid_credentials(
    service,
    repository,
    login_payload,
):
    """Accept valid credentials for an active user."""
    user = SimpleNamespace(
        email="traveler@example.com",
        password_hash="secure-test-hash",
        is_active=True,
    )
    repository.get_by_email.return_value = user

    with patch(
        "app.services.auth_service.verify_password",
        return_value=True,
    ) as mock_verify:
        result = service.authenticate(login_payload)

    mock_verify.assert_called_once_with(
        "TripMateDemo!2026",
        "secure-test-hash",
    )
    assert result is user


def test_authenticate_rejects_unknown_user(
    service,
    repository,
    login_payload,
):
    """Reject an unknown account."""
    repository.get_by_email.return_value = None

    with patch("app.services.auth_service.verify_password") as mock_verify:
        assert service.authenticate(login_payload) is None

    mock_verify.assert_not_called()


def test_authenticate_rejects_incorrect_password(
    service,
    repository,
    login_payload,
):
    """Reject an incorrect password."""
    user = SimpleNamespace(
        email="traveler@example.com",
        password_hash="secure-test-hash",
        is_active=True,
    )
    repository.get_by_email.return_value = user

    with patch(
        "app.services.auth_service.verify_password",
        return_value=False,
    ):
        assert service.authenticate(login_payload) is None


def test_authenticate_rejects_user_without_password_hash(
    service,
    repository,
    login_payload,
):
    """Reject accounts without a password hash."""
    user = SimpleNamespace(
        email="traveler@example.com",
        password_hash=None,
        is_active=True,
    )
    repository.get_by_email.return_value = user

    with patch("app.services.auth_service.verify_password") as mock_verify:
        assert service.authenticate(login_payload) is None

    mock_verify.assert_not_called()


def test_authenticate_rejects_inactive_user(
    service,
    repository,
    login_payload,
):
    """Reject inactive accounts even when the password is valid."""
    user = SimpleNamespace(
        email="traveler@example.com",
        password_hash="secure-test-hash",
        is_active=False,
    )
    repository.get_by_email.return_value = user

    with patch(
        "app.services.auth_service.verify_password",
        return_value=True,
    ):
        assert service.authenticate(login_payload) is None
        