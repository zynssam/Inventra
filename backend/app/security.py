"""
app/security.py — password hashing + JWT helpers.

Uses bcrypt directly (bypassing passlib which has Python 3.14 / newer bcrypt
compat issues) and HS256 JWT via python-jose.
Access tokens expire after settings.ACCESS_TOKEN_EXPIRE_MINUTES (8 h).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(subject: str | int, extra: dict | None = None) -> str:
    """Create a signed JWT with a `sub` claim and an 8-hour expiry."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict = {"sub": str(subject), "iat": now, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT.  Returns the payload dict.
    Raises JWTError (caught by dependencies.py) on any failure.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
