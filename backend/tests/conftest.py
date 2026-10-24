"""
tests/conftest.py — shared pytest fixtures.

Uses an in-memory SQLite database. The key challenge with SQLite in-memory
databases is that each connection gets its own isolated DB. We solve this by:
  - Creating ONE persistent connection for the whole test function
  - Running all DB operations (test setup AND request handlers) on that
    single connection via a sessionmaker bound to it directly
  - Using begin()/rollback() for isolation between tests

This approach guarantees that rows inserted by test helpers are visible to
the FastAPI request handlers that run inside TestClient.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session

from app.database import get_db
from app.main import app
from app.models import Base, User, UserRole
from app.security import hash_password


@pytest.fixture(scope="function")
def db_engine():
    """One engine per test; tables created fresh each time."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Force SQLite to use a single shared connection for the engine
    # so all sessions (test helpers + request handlers) see the same data.
    connection = engine.connect()

    # Create all tables on this connection
    Base.metadata.create_all(bind=connection)

    yield connection, engine

    connection.close()
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Session bound to the single shared connection."""
    connection, engine = db_engine
    SessionFactory = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionFactory()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient with the in-memory DB injected via dependency override.
    All request handlers share the same session (and thus same connection)
    as the test setup code, so rows are always visible.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def create_user(
    db: Session,
    name: str = "Admin",
    email: str = "admin@test.com",
    password: str = "password123",
    role: str = "admin",
) -> User:
    u = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole(role),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_token(client, email: str = "admin@test.com", password: str = "password123") -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
