
"""Database repository for TripMate AI trip records."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.trip import Trip


class TripRepository:
    """Encapsulate database operations for Trip records."""

    def __init__(self, db: Session) -> None:
        """Initialize the repository with a database session."""
        self.db = db

    def create(self, trip: Trip) -> Trip:
        """Add a trip to the current transaction without committing."""
        self.db.add(trip)
        self.db.flush()
        self.db.refresh(trip)
        return trip

    def get_by_id(self, trip_id: uuid.UUID) -> Trip | None:
        """Retrieve a trip by its primary key."""
        statement = select(Trip).where(Trip.id == trip_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id_for_user(
        self,
        trip_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Trip | None:
        """Retrieve a trip only if it belongs to the specified user."""
        statement = select(Trip).where(
            Trip.id == trip_id,
            Trip.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trip]:
        """List a user's trips, newest first."""
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        if offset < 0:
            raise ValueError("offset cannot be negative")

        statement = (
            select(Trip)
            .where(Trip.user_id == user_id)
            .order_by(Trip.created_at.desc(), Trip.id.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.execute(statement).scalars().all())
