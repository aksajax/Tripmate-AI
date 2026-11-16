
"""Pydantic schemas for TripMate AI trip APIs."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CurrencyCode = Literal["INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD"]
TravelStyle = Literal["budget", "balanced", "luxury", "adventure", "relaxed"]


class TripCreate(BaseModel):
    """Validated input for creating a trip."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    origin: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    travelers: int = Field(default=1, ge=1, le=12)
    budget: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=2)
    currency: CurrencyCode = "INR"
    travel_style: TravelStyle = "balanced"
    special_requirements: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_trip_dates_and_locations(self) -> "TripCreate":
        """Validate date order and distinct locations."""
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")

        if self.origin.casefold() == self.destination.casefold():
            raise ValueError("Origin and destination must be different")

        return self


class TripResponse(BaseModel):
    """Public response representation of a saved trip."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    origin: str
    destination: str
    start_date: date
    end_date: date
    travelers: int
    budget: Decimal
    currency: str
    travel_style: str
    special_requirements: str | None
    status: str
    created_at: datetime
    updated_at: datetime
