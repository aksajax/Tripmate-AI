
"""PostgreSQL engine and session configuration for TripMate AI."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Create the engine lazily; this does not connect until a database operation
# requires a connection.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    echo=settings.db_echo_sql,
)

# SessionLocal creates independent database sessions for requests and services.
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
