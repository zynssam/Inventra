"""
app/dependencies.py — FastAPI dependencies for auth and RBAC.

Works with Member A's real User model:
  - User.full_name (not .name)
  - User.role is plain str; values: admin | store_manager | viewer
  - User.is_active (bool)
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
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
        raise ApiError(401, "INVALID_CREDENTIALS", "Missing Authorization header")
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise ApiError(401, "INVALID_CREDENTIALS", "Invalid token payload")
    except JWTError:
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid or expired token")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise ApiError(401, "INVALID_CREDENTIALS", "User not found or inactive")
    return user


def require_role(*roles: str):
    """
    Factory that returns a FastAPI dependency function enforcing role membership.
    Usage:  current_user: User = Depends(require_role("admin", "store_manager"))
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ApiError(403, "FORBIDDEN", f"Required role(s): {', '.join(roles)}")
        return current_user
    return dependency
