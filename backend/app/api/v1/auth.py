
"""Authentication endpoints for TripMate AI."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tokens import create_access_token
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DatabaseSession) -> AuthService:
    """Build the authentication service for the current request."""
    return AuthService(UserRepository(db))


AuthServiceDependency = Annotated[
    AuthService,
    Depends(get_auth_service),
]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    service: AuthServiceDependency,
) -> UserResponse:
    """Register a new user account."""
    try:
        user = service.register(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    service: AuthServiceDependency,
) -> TokenResponse:
    """Authenticate a user and issue an access token."""
    user = service.authenticate(payload)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()

    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.app_secret_key.get_secret_value(),
        expires_in_seconds=settings.access_token_expire_minutes * 60,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
