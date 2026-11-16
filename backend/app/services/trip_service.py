
"""Business logic for creating and retrieving TripMate AI trips."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.trip import Trip
from app.repositories.audit_repository import AuditRepository
from app.repositories.trip_repository import TripRepository


SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD"}
SUPPORTED_TRAVEL_STYLES = {"budget", "balanced", "luxury", "adventure", "relaxed"}


class TripService:
    """Validate trip requests and coordinate trip persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TripRepository(db)
        self.audit_repository = AuditRepository(db)

    @staticmethod
    def _validate_text(value: str, field_name: str, max_length: int = 200) -> str:
        """Return normalized non-empty text or raise ValueError."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be text")

        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")

        if len(normalized) > max_length:
            raise ValueError(f"{field_name} cannot exceed {max_length} characters")

        return normalized

    def create_trip(
        self,
        *,
        user_id: uuid.UUID,
        origin: str,
        destination: str,
        start_date: date,
        end_date: date,
        travelers: int,
        budget: Decimal,
        currency: str = "INR",
        travel_style: str = "balanced",
        special_requirements: str | None = None,
        commit: bool = True,
    ) -> Trip:
        """Validate, persist, and audit a new trip draft.

        Set commit=False when a caller needs to commit this operation
        atomically with additional database records.
        """
        if not isinstance(user_id, uuid.UUID):
            raise ValueError("user_id must be a UUID")

        if not isinstance(commit, bool):
            raise ValueError("commit must be a boolean")

        origin = self._validate_text(origin, "origin")
        destination = self._validate_text(destination, "destination")

        if origin.casefold() == destination.casefold():
            raise ValueError("Origin and destination must be different")

        if not isinstance(start_date, date):
            raise ValueError("start_date must be a valid date")

        if not isinstance(end_date, date):
            raise ValueError("end_date must be a valid date")

        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")

        if not isinstance(travelers, int) or isinstance(travelers, bool):
            raise ValueError("travelers must be an integer")

        if not 1 <= travelers <= 12:
            raise ValueError("travelers must be between 1 and 12")

        try:
            budget = Decimal(str(budget))
        except Exception as exc:
            raise ValueError("budget must be a valid decimal amount") from exc

        if not budget.is_finite() or budget < 0:
            raise ValueError("budget must be finite and non-negative")

        if budget.as_tuple().exponent < -2:
            raise ValueError("budget cannot have more than two decimal places")

        if budget >= Decimal("10000000000"):
            raise ValueError("budget exceeds the supported maximum")

        if not isinstance(currency, str):
            raise ValueError("currency must be text")

        currency = currency.strip().upper()
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency: {currency}. "
                f"Supported currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
            )

        if not isinstance(travel_style, str):
            raise ValueError("travel_style must be text")

        travel_style = travel_style.strip().lower()
        if travel_style not in SUPPORTED_TRAVEL_STYLES:
            raise ValueError(
                f"Unsupported travel style: {travel_style}. "
                f"Supported styles: {', '.join(sorted(SUPPORTED_TRAVEL_STYLES))}"
            )

        if special_requirements is not None:
            special_requirements = self._validate_text(
                special_requirements,
                "special_requirements",
                max_length=5000,
            )

        trip = Trip(
            user_id=user_id,
            origin=origin,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            travelers=travelers,
            budget=budget,
            currency=currency,
            travel_style=travel_style,
            special_requirements=special_requirements,
            status="draft",
        )

        try:
            saved_trip = self.repository.create(trip)

            self.audit_repository.record_event(
                actor_user_id=user_id,
                action="trip.created",
                entity_type="trip",
                entity_id=saved_trip.id,
                details={
                    "origin": origin,
                    "destination": destination,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "travelers": travelers,
                    "currency": currency,
                    "travel_style": travel_style,
                },
            )

            if commit:
                self.db.commit()
                self.db.refresh(saved_trip)

            return saved_trip

        except Exception:
            self.db.rollback()
            raise

    def get_trip(self, trip_id: uuid.UUID) -> Trip | None:
        """Retrieve a trip by ID.

        The API boundary must enforce ownership before returning trip details.
        """
        return self.repository.get_by_id(trip_id)

    def list_user_trips(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trip]:
        """List trips for a specified user."""
        return self.repository.list_by_user(
            user_id,
            limit=limit,
            offset=offset,
        )
