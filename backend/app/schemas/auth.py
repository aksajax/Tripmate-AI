
"""Pydantic schemas for TripMate AI authentication APIs."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    """Validate data submitted during account registration."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Perform basic email format validation."""
        value = value.lower()

        if not re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
            r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?)+",
            value,
        ):
            raise ValueError("A valid email address is required")

        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        """Reject display names containing only whitespace."""
        if not value.strip():
            raise ValueError("display_name cannot be empty")

        return value


class UserLogin(BaseModel):
    """Validate credentials submitted during login."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize the email address for account lookup."""
        value = value.strip().lower()

        if not value or "@" not in value:
            raise ValueError("A valid email address is required")

        return value


class TokenResponse(BaseModel):
    """Represent an access-token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)


class UserResponse(BaseModel):
    """Expose safe public user fields without password data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
