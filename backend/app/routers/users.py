"""
app/routers/users.py — GET/POST/PATCH /users (admin only)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import User, UserRole
from app.schemas import Page, UserCreate, UserOut, UserUpdate
from app.security import hash_password
from app.services.audit_service import audit

router = APIRouter(prefix="/users", tags=["users"])

ADMIN = Depends(require_role("admin"))


@router.get("", response_model=Page[UserOut])
def list_users(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = ADMIN,
):
    q = db.query(User)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=[UserOut.model_validate(u) for u in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    existing = db.query(User).filter(User.email == body.email).one_or_none()
    if existing:
        raise ApiError(409, "DUPLICATE_SKU", "Email already registered", field="email")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole(body.role),
    )
    db.add(user)
    db.flush()
    audit(db, current_user, "USER_CREATE", "user", user.id, {"email": user.email, "role": user.role.value})
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = ADMIN):
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "NOT_FOUND", f"User {user_id} not found")
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "NOT_FOUND", f"User {user_id} not found")
    before = {"role": user.role.value, "is_active": user.is_active}
    if body.name is not None:
        user.name = body.name
    if body.role is not None:
        user.role = UserRole(body.role)
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    audit(db, current_user, "USER_UPDATE", "user", user.id, {"before": before})
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
