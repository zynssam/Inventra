"""app/routers/users.py — /users CRUD (admin only)"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import User
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
    items = q.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    existing = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if existing:
        raise ApiError(409, "DUPLICATE_EMAIL", "Email already registered", field="email")
    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.flush()
    audit(db, current_user, "USER_CREATE", "user", user.id, {"email": user.email, "role": user.role})
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = ADMIN):
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "NOT_FOUND", f"User {user_id} not found")
    return user


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
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(user, k, v)
    audit(db, current_user, "USER_UPDATE", "user", user_id, updates)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "NOT_FOUND", f"User {user_id} not found")
    if user.id == current_user.id:
        raise ApiError(400, "VALIDATION_ERROR", "Cannot delete yourself")
    audit(db, current_user, "USER_DELETE", "user", user_id, {"email": user.email})
    db.delete(user)
    db.commit()
