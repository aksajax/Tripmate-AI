
"""Pydantic schemas for TripMate AI itineraries."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=300),
]

MoneyAmount = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2),
]

CurrencyCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]{3}$"),
]


class ItineraryActivity(BaseModel):
    """One activity or planned stop in a day's itinerary."""

    model_config = ConfigDict(extra="forbid")

    title: NonEmptyText
    description: str = Field(default="", max_length=2000)
    location: str | None = Field(default=None, max_length=300)
    start_time: str | None = Field(
        default=None,
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="Optional local time in HH:MM 24-hour format.",
    )
    end_time: str | None = Field(
        default=None,
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="Optional local time in HH:MM 24-hour format.",
    )
    estimated_cost: MoneyAmount = Decimal("0.00")
    currency: CurrencyCode = "INR"
    source_reference: str | None = Field(default=None, max_length=500)


class ItineraryDay(BaseModel):
    """Activities and estimated spending for one calendar day."""

    model_config = ConfigDict(extra="forbid")

    day_number: int = Field(ge=1)
    date: date
    title: NonEmptyText
    summary: str = Field(default="", max_length=2000)
    activities: list[ItineraryActivity] = Field(
        default_factory=list,
        max_length=50,
    )
    estimated_total: MoneyAmount = Decimal("0.00")
    currency: CurrencyCode = "INR"

    @model_validator(mode="after")
    def validate_activity_times(self) -> "ItineraryDay":
        """Ensure provided end times do not precede their start times."""
        for activity in self.activities:
            if (
                activity.start_time is not None
                and activity.end_time is not None
                and activity.end_time < activity.start_time
            ):
                raise ValueError(
                    f"Activity '{activity.title}' ends before it starts"
                )
        return self


class ItineraryBudget(BaseModel):
    """Cost breakdown for the entire proposed itinerary."""

    model_config = ConfigDict(extra="forbid")

    currency: CurrencyCode = "INR"
    flights: MoneyAmount = Decimal("0.00")
    accommodation: MoneyAmount = Decimal("0.00")
    local_transport: MoneyAmount = Decimal("0.00")
    food: MoneyAmount = Decimal("0.00")
    activities: MoneyAmount = Decimal("0.00")
    other: MoneyAmount = Decimal("0.00")
    total_estimated: MoneyAmount = Decimal("0.00")
    user_budget: MoneyAmount
    remaining_budget: Decimal = Decimal("0.00")

    @model_validator(mode="after")
    def calculate_budget_totals(self) -> "ItineraryBudget":
        """Calculate totals from the cost categories using Decimal arithmetic."""
        categories = (
            self.flights
            + self.accommodation
            + self.local_transport
            + self.food
            + self.activities
            + self.other
        )

        calculated_remaining = self.user_budget - categories

        self.total_estimated = categories
        self.remaining_budget = calculated_remaining.quantize(
            Decimal("0.01")
        )
        return self


class ItineraryResponse(BaseModel):
    """Complete proposed itinerary returned by the planning workflow."""

    model_config = ConfigDict(extra="forbid")

    itinerary_id: str = Field(min_length=1, max_length=100)
    trip_id: str = Field(min_length=1, max_length=100)
    version: int = Field(default=1, ge=1)
    status: Literal[
        "draft",
        "proposed",
        "pending_approval",
        "approved",
        "rejected",
        "superseded",
    ] = "draft"

    origin: NonEmptyText
    destination: NonEmptyText
    start_date: date
    end_date: date
    travelers: int = Field(ge=1, le=12)

    days: list[ItineraryDay] = Field(min_length=1, max_length=60)
    budget: ItineraryBudget

    provider_sources: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="References identifying sources used by the planner.",
    )
    generated_at: datetime
    warnings: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_itinerary_consistency(self) -> "ItineraryResponse":
        """Validate the date range and the itinerary's daily schedule."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")

        expected_days = (self.end_date - self.start_date).days + 1

        if len(self.days) != expected_days:
            raise ValueError(
                f"Expected {expected_days} itinerary days, "
                f"received {len(self.days)}"
            )

        for index, itinerary_day in enumerate(self.days, start=1):
            expected_date = self.start_date.fromordinal(
                self.start_date.toordinal() + index - 1
            )

            if itinerary_day.day_number != index:
                raise ValueError(
                    "Itinerary day numbers must be sequential starting at 1"
                )

            if itinerary_day.date != expected_date:
                raise ValueError(
                    f"Day {index} must use date {expected_date.isoformat()}"
                )

        if self.budget.total_estimated > self.budget.user_budget:
            self.warnings.append("Estimated itinerary exceeds the user's budget.")

        return self
