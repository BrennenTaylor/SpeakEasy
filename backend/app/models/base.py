from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Return the current UTC time for Python-side column defaults."""
    return datetime.now(UTC)
