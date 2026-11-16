
"""Integration tests for the TripMate AI database."""

from uuid import uuid4

from sqlalchemy import delete, inspect, select, text

from app.db.models import AuditEvent, Base
from app.db.session import SessionLocal, engine
from app.repositories.audit_repository import AuditRepository


def test_expected_orm_tables_are_registered() -> None:
    """Ensure all expected ORM models are registered."""
    expected_tables = {
        "users",
        "trips",
        "itineraries",
        "audit_events",
    }

    registered_tables = set(Base.metadata.tables.keys())

    assert expected_tables.issubset(registered_tables)


def test_expected_tables_exist_in_postgresql() -> None:
    """Ensure migrations created the expected application tables."""
    expected_tables = {
        "users",
        "trips",
        "itineraries",
        "audit_events",
        "alembic_version",
    }

    database_tables = set(inspect(engine).get_table_names())

    assert expected_tables.issubset(database_tables)


def test_database_session_executes_query() -> None:
    """Ensure a database session can execute a simple query."""
    with SessionLocal() as db:
        result = db.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_audit_event_persists_in_postgresql() -> None:
    """Verify an audit event can be committed and read back."""
    correlation_id = f"test-{uuid4()}"
    event_id = None

    try:
        with SessionLocal() as db:
            repository = AuditRepository(db)

            event = repository.record_event(
                action="test.database_persistence",
                entity_type="integration_test",
                entity_id=correlation_id,
                details={"test": True, "source": "pytest"},
                correlation_id=correlation_id,
            )

            event_id = event.id
            db.commit()

        # Use a separate session to verify committed persistence.
        with SessionLocal() as db:
            saved_event = db.execute(
                select(AuditEvent).where(AuditEvent.id == event_id)
            ).scalar_one_or_none()

            assert saved_event is not None
            assert saved_event.action == "test.database_persistence"
            assert saved_event.entity_type == "integration_test"
            assert saved_event.entity_id == correlation_id
            assert saved_event.details == {
                "test": True,
                "source": "pytest",
            }
            assert saved_event.correlation_id == correlation_id

    finally:
        # Remove only the event created by this test.
        if event_id is not None:
            with SessionLocal() as db:
                db.execute(
                    delete(AuditEvent).where(AuditEvent.id == event_id)
                )
                db.commit()
