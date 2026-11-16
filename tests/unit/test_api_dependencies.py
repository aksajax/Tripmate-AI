
"""Unit tests for API authentication dependencies."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.tokens import create_access_token
from app.db.models.user import User
from app.repositories.user_repository import UserRepository


@pytest.fixture
def secret_key() -> str:
    """Return the configured application secret."""
    return get_settings().app_secret_key.get_secret_value()


@pytest.fixture
def active_user() -> SimpleNamespace:
    """Create a lightweight active user for tests."""
    return SimpleNamespace(
        id=uuid4(),
        email="traveler@example.com",
        display_name="Test Traveler",
        is_active=True,
    )


def make_credentials(token: str) -> HTTPAuthorizationCredentials:
    """Wrap a token in HTTP Bearer credentials."""
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )


def test_valid_token_returns_active_user(
    monkeypatch: pytest.MonkeyPatch,
    secret_key: str,
    active_user: SimpleNamespace,
) -> None:
    token = create_access_token(str(active_user.id), secret_key)
    repository = Mock(spec=UserRepository)
    repository.get_by_id.return_value = active_user

    monkeypatch.setattr(
        "app.api.dependencies.UserRepository",
        lambda db: repository,
    )

    result = get_current_user(make_credentials(token), Mock())

    assert result is active_user
    repository.get_by_id.assert_called_once_with(active_user.id)


def test_missing_credentials_are_rejected() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None, Mock())

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_rejected(
    secret_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Mock(spec=UserRepository)
    monkeypatch.setattr(
        "app.api.dependencies.UserRepository",
        lambda db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(make_credentials("invalid.token.value"), Mock())

    assert exc_info.value.status_code == 401
    repository.get_by_id.assert_not_called()


def test_unknown_user_is_rejected(
    secret_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    token = create_access_token(str(user_id), secret_key)

    repository = Mock(spec=UserRepository)
    repository.get_by_id.return_value = None

    monkeypatch.setattr(
        "app.api.dependencies.UserRepository",
        lambda db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(make_credentials(token), Mock())

    assert exc_info.value.status_code == 401


def test_inactive_user_is_rejected(
    secret_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    token = create_access_token(str(user_id), secret_key)
    inactive_user = SimpleNamespace(id=user_id, is_active=False)

    repository = Mock(spec=UserRepository)
    repository.get_by_id.return_value = inactive_user

    monkeypatch.setattr(
        "app.api.dependencies.UserRepository",
        lambda db: repository,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(make_credentials(token), Mock())

    assert exc_info.value.status_code == 401
