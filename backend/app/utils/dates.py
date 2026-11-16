
"""Date utilities for TripMate AI travel planning."""

from datetime import date, datetime, timedelta


def validate_trip_dates(
    start_date: date,
    end_date: date,
) -> None:
    """Validate a trip's date range.

    Raises:
        TypeError: If either argument is not a date or datetime.
        ValueError: If the end date is before the start date.
    """
    if (
        not isinstance(start_date, date)
        or isinstance(start_date, datetime)
    ):
        raise TypeError("start_date must be a date")

    if (
        not isinstance(end_date, date)
        or isinstance(end_date, datetime)
    ):
        raise TypeError("end_date must be a date")

    if end_date < start_date:
        raise ValueError("end_date cannot be before start_date")


def trip_duration_days(
    start_date: date,
    end_date: date,
) -> int:
    """Return the number of calendar days covered by a trip.

    Both the start and end dates are included. A trip from Monday to
    Wednesday therefore covers three calendar days.
    """
    validate_trip_dates(start_date, end_date)
    return (end_date - start_date).days + 1


def trip_nights(
    start_date: date,
    end_date: date,
) -> int:
    """Return the number of nights between arrival and departure dates."""
    validate_trip_dates(start_date, end_date)
    return (end_date - start_date).days


def get_trip_dates(
    start_date: date,
    end_date: date,
) -> list[date]:
    """Return every calendar date in the trip, including both endpoints."""
    validate_trip_dates(start_date, end_date)

    total_days = trip_duration_days(start_date, end_date)

    return [
        start_date + timedelta(days=offset)
        for offset in range(total_days)
    ]
