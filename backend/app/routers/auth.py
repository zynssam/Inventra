"""app/routers/auth.py — POST /auth/login, POST /auth/change-password"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
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
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password")
    if not user.is_active:
        raise ApiError(403, "FORBIDDEN", "Account is deactivated")
    token = create_access_token(subject=user.id, extra={"role": user.role})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise ApiError(400, "INVALID_CREDENTIALS", "Current password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
