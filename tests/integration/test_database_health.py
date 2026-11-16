
"""Database connectivity health tests for TripMate AI."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine


def test_postgresql_is_reachable() -> None:
    """Verify PostgreSQL accepts a connection and executes a query."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_database_engine_uses_postgresql() -> None:
    """Ensure the configured database engine uses PostgreSQL."""
    assert engine.dialect.name == "postgresql"
