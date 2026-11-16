
"""Shared SQLAlchemy declarative base for TripMate AI models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class inherited by all database models."""

    pass
