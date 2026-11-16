
"""Authenticated user profile endpoints for TripMate AI."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

CurrentUserDependency = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: CurrentUserDependency) -> UserResponse:
    """Return the authenticated user's public profile."""
    return UserResponse.model_validate(current_user)
