"""
app/_temp/database_temp.py  — TEMPORARY stand-in for Member A's database.py

⚠️  DELETE THIS FILE and remove the shim in app/database.py once Member A
    delivers backend/app/database.py.
"""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app._temp.models_temp import Base

# SQLite connect_args only needed for SQLite databases
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables — used in tests and dev startup."""
    Base.metadata.create_all(bind=engine)
