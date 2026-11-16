
"""Standard schemas for TripMate AI travel-provider results."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=300),
]

CurrencyCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]{3}$"),
]

MoneyAmount = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2),
]


class ProviderMetadata(BaseModel):
    """Describe where provider data came from and when it was retrieved."""

    model_config = ConfigDict(extra="forbid")

    provider_name: NonEmptyText
    source_type: Literal["live", "mock", "cache"] = "mock"
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    verified: bool = False
    source_reference: str | None = Field(default=None, max_length=500)

    def mark_verified(self) -> "ProviderMetadata":
        """Return a verified copy only when the caller has evidence to support it."""
        return self.model_copy(update={"verified": True})


class FlightResult(BaseModel):
    """Normalized flight-search result."""

    model_config = ConfigDict(extra="forbid")

    provider: ProviderMetadata
    airline: NonEmptyText
    flight_number: str | None = Field(default=None, max_length=30)
    origin: NonEmptyText
    destination: NonEmptyText
    departure_at: datetime
    arrival_at: datetime
    price: MoneyAmount
    currency: CurrencyCode
    stops: int = Field(default=0, ge=0, le=10)

    @property
    def duration_minutes(self) -> int:
        """Calculate flight duration from timezone-aware timestamps."""
        if (
            self.departure_at.tzinfo is None
            or self.arrival_at.tzinfo is None
        ):
            raise ValueError(
                "Flight departure and arrival timestamps must include timezones"
            )

        seconds = (
            self.arrival_at - self.departure_at
        ).total_seconds()

        if seconds < 0:
            raise ValueError("Flight arrival cannot precede departure")

        return int(seconds // 60)


class HotelResult(BaseModel):
    """Normalized hotel-search result."""

    model_config = ConfigDict(extra="forbid")

    provider: ProviderMetadata
    hotel_name: NonEmptyText
    destination: NonEmptyText
    check_in: datetime
    check_out: datetime
    nightly_price: MoneyAmount
    total_price: MoneyAmount
    currency: CurrencyCode
    rating: float | None = Field(default=None, ge=0, le=5)
    booking_url: str | None = Field(default=None, max_length=1000)


class WeatherResult(BaseModel):
    """Normalized weather forecast result."""

    model_config = ConfigDict(extra="forbid")

    provider: ProviderMetadata
    location: NonEmptyText
    forecast_at: datetime
    temperature_celsius: float = Field(ge=-100, le=70)
    condition: NonEmptyText
    precipitation_probability: float | None = Field(
        default=None, ge=0, le=100
    )


class DestinationResult(BaseModel):
    """Normalized destination-information result."""

    model_config = ConfigDict(extra="forbid")

    provider: ProviderMetadata
    destination: NonEmptyText
    summary: Annotated[
        str,
        StringConstraints(strip_whitespace=True, max_length=5000),
    ]
    highlights: list[NonEmptyText] = Field(default_factory=list, max_length=30)
    best_time_to_visit: str | None = Field(default=None, max_length=500)


class CurrencyConversionResult(BaseModel):
    """Normalized currency-conversion result."""

    model_config = ConfigDict(extra="forbid")

    provider: ProviderMetadata
    base_currency: CurrencyCode
    target_currency: CurrencyCode
    exchange_rate: Decimal = Field(
        gt=0, max_digits=18, decimal_places=8
    )
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None

    def convert(self, amount: Decimal) -> Decimal:
        """Convert an amount using this result's exchange rate."""
        if amount < 0:
            raise ValueError("Amount cannot be negative")

        return (amount * self.exchange_rate).quantize(
            Decimal("0.01")
        )
