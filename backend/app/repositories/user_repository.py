
"""Database repository for TripMate AI user accounts."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    """Handle database operations for user accounts."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
    ) -> User:
        """Add a user to the current transaction without committing."""
        user = User(
            email=email.strip().lower(),
            display_name=display_name.strip(),
            password_hash=password_hash,
            is_active=True,
            is_superuser=False,
        )

        try:
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise ValueError(
                "A user with this email address already exists"
            ) from None
        except Exception:
            self.db.rollback()
            raise

    def get_by_email(self, email: str) -> User | None:
        """Find a user by normalized email address."""
        normalized_email = email.strip().lower()

        statement = select(User).where(User.email == normalized_email)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Find a user by their UUID."""
        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        """Check whether an email address is already registered."""
        statement = select(User.id).where(
            User.email == email.strip().lower()
        )
        return self.db.execute(statement).scalar_one_or_none() is not None
