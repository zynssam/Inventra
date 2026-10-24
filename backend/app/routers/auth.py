"""
app/routers/auth.py — POST /auth/login, GET /auth/me, POST /auth/change-password
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ApiError
from app.models import User
from app.schemas import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    if not user.is_active:
        raise ApiError(401, "INVALID_CREDENTIALS", "Account is deactivated")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, current_user.password_hash):
        raise ApiError(400, "INVALID_CREDENTIALS", "Old password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
