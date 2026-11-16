
"""Unit tests for TripMate AI date utilities."""

from datetime import date, datetime

import pytest

from app.utils.dates import (
    get_trip_dates,
    trip_duration_days,
    trip_nights,
    validate_trip_dates,
)


def test_trip_duration_includes_start_and_end_dates() -> None:
    assert trip_duration_days(date(2027, 1, 10), date(2027, 1, 15)) == 6


def test_trip_nights_excludes_departure_day() -> None:
    assert trip_nights(date(2027, 1, 10), date(2027, 1, 15)) == 5


def test_get_trip_dates_returns_all_dates_in_order() -> None:
    dates = get_trip_dates(date(2027, 1, 10), date(2027, 1, 12))

    assert dates == [
        date(2027, 1, 10),
        date(2027, 1, 11),
        date(2027, 1, 12),
    ]


def test_same_start_and_end_date_is_one_day_and_zero_nights() -> None:
    day = date(2027, 1, 10)

    assert trip_duration_days(day, day) == 1
    assert trip_nights(day, day) == 0
    assert get_trip_dates(day, day) == [day]


def test_end_date_before_start_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="end_date cannot be before start_date"):
        validate_trip_dates(date(2027, 1, 15), date(2027, 1, 10))


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2027-01-10", date(2027, 1, 15)),
        (date(2027, 1, 10), "2027-01-15"),
        (datetime(2027, 1, 10), date(2027, 1, 15)),
        (date(2027, 1, 10), datetime(2027, 1, 15)),
    ],
)
def test_non_date_arguments_are_rejected(
    start_date: object,
    end_date: object,
) -> None:
    with pytest.raises(TypeError):
        validate_trip_dates(start_date, end_date)  # type: ignore[arg-type]


def test_leap_year_dates_are_handled() -> None:
    dates = get_trip_dates(date(2028, 2, 28), date(2028, 3, 1))

    assert dates == [
        date(2028, 2, 28),
        date(2028, 2, 29),
        date(2028, 3, 1),
    ]
