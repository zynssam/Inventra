"""
tests/conftest.py — shared pytest fixtures.

IMPORTANT: DATABASE_URL must be set to SQLite BEFORE importing app modules,
so the lazy engine picks up the test URL instead of the production Postgres URL.
"""
from __future__ import annotations

import os
import pytest

# ── Override the DB URL before any app code loads ──────────────────────────
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-32-characters-ok"

from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import create_engine                 # noqa: E402
from sqlalchemy.orm import sessionmaker, Session     # noqa: E402

from app.database import get_db                      # noqa: E402
from app.main import app                             # noqa: E402
from app.models import Base, User                    # noqa: E402
from app.security import hash_password               # noqa: E402


@pytest.fixture(scope="function")
def db_engine():
    """One in-memory SQLite engine per test, with a single persistent connection."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    connection = engine.connect()
    Base.metadata.create_all(bind=connection)
    yield connection, engine
    connection.close()
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    connection, _ = db_engine
    SessionFactory = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionFactory()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session: Session):
    """TestClient with test DB injected. Lifespan is skipped (app.router = False)."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # lifespan=False prevents the startup event from trying to connect to Postgres
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def create_user(
    db: Session,
    full_name: str = "Admin User",
    email: str = "admin@test.com",
    password: str = "password123",
    role: str = "admin",
) -> User:
    u = User(full_name=full_name, email=email, password_hash=hash_password(password), role=role)
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
