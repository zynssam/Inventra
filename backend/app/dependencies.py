"""
app/dependencies.py — FastAPI dependency functions for auth and RBAC.

get_current_user   — validates JWT, returns User ORM object
require_role(*roles) — factory that returns a Depends() asserting the user has one of the given roles
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "Missing authentication token")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise ApiError(401, "INVALID_CREDENTIALS", "Invalid token")
    except JWTError:
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid or expired token")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise ApiError(401, "INVALID_CREDENTIALS", "User not found or inactive")
    return user


def require_role(*roles: str):
    """
    Factory returning a dependency that asserts the current user has one of
    the given roles.  E.g. Depends(require_role("admin", "storekeeper")).
    """
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise ApiError(403, "FORBIDDEN", f"Role '{user.role.value}' cannot perform this action")
        return user

    return _check
