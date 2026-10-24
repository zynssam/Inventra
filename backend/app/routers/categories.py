"""
app/routers/categories.py — /categories endpoints
Roles: GET any logged-in; POST/PATCH admin+storekeeper; DELETE admin only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Category, Product, User
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.audit_service import audit

router = APIRouter(prefix="/categories", tags=["categories"])


def _with_count(cat: Category, db: Session) -> CategoryOut:
    count = db.query(Product).filter(Product.category_id == cat.id).count()
    out = CategoryOut.model_validate(cat)
    out.product_count = count
    return out


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "storekeeper", "viewer")),
):
    cats = db.query(Category).order_by(Category.name).all()
    return [_with_count(c, db) for c in cats]


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    if db.query(Category).filter(Category.name == body.name).one_or_none():
        raise ApiError(409, "DUPLICATE_SKU", "Category name already exists", field="name")
    cat = Category(name=body.name, description=body.description)
    db.add(cat)
    db.flush()
    audit(db, current_user, "CATEGORY_CREATE", "category", cat.id, {"name": cat.name})
    db.commit()
    db.refresh(cat)
    return _with_count(cat, db)


@router.patch("/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    body: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    cat = db.get(Category, cat_id)
    if cat is None:
        raise ApiError(404, "NOT_FOUND", f"Category {cat_id} not found")
    if body.name is not None:
        cat.name = body.name
    if body.description is not None:
        cat.description = body.description
    audit(db, current_user, "CATEGORY_UPDATE", "category", cat.id)
    db.commit()
    db.refresh(cat)
    return _with_count(cat, db)


@router.delete("/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    cat = db.get(Category, cat_id)
    if cat is None:
        raise ApiError(404, "NOT_FOUND", f"Category {cat_id} not found")
    dep_count = db.query(Product).filter(Product.category_id == cat_id).count()
    if dep_count > 0:
        raise ApiError(409, "HAS_DEPENDENCIES", f"{dep_count} product(s) use this category")
    audit(db, current_user, "CATEGORY_DELETE", "category", cat_id)
    db.delete(cat)
    db.commit()
