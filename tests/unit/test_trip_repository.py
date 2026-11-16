
"""Unit tests for user-scoped trip repository queries."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.repositories.trip_repository import TripRepository

    
def test_get_by_id_for_user_returns_matching_trip() -> None:
    """Return the trip when the database finds a matching record."""
    trip_id = uuid4()
    user_id = uuid4()
    trip = SimpleNamespace(id=trip_id, user_id=user_id)

    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = trip

    repository = TripRepository(db)
    result = repository.get_by_id_for_user(
        trip_id=trip_id,
        user_id=user_id,
    )

    assert result is trip
    db.execute.assert_called_once()

    statement = db.execute.call_args.args[0]
    compiled = statement.compile()

    assert "trips.id" in str(compiled)
    assert "trips.user_id" in str(compiled)
    assert trip_id in compiled.params.values()
    assert user_id in compiled.params.values()


def test_get_by_id_for_user_returns_none_when_no_match() -> None:
    """Return None when no trip matches both IDs."""
    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    repository = TripRepository(db)
    result = repository.get_by_id_for_user(
        trip_id=uuid4(),
        user_id=uuid4(),
    )

    assert result is None
    db.execute.assert_called_once()
    db.execute.return_value.scalar_one_or_none.assert_called_once()
