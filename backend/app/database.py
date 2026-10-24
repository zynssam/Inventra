"""
app/database.py — SQLAlchemy engine, session, and get_db dependency.

Uses Member A's real models. Engine is created lazily (on first use)
so that importing this module during tests with SQLite override doesn't
attempt to connect to PostgreSQL.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


# Expose engine for create_tables / tests
@property
def engine():
    return _get_engine()


def get_db() -> Generator[Session, None, None]:
    _get_engine()  # ensure initialized
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables — used in tests and dev startup."""
    from app.models import Base
    Base.metadata.create_all(bind=_get_engine())
