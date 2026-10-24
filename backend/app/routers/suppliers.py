"""app/routers/suppliers.py — /suppliers CRUD"""
from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Supplier, User
from app.schemas import Page, SupplierCreate, SupplierOut, SupplierUpdate
from app.services.audit_service import audit
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=Page[SupplierOut])
def list_suppliers(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "store_manager", "viewer")),
):
    total = db.query(Supplier).count()
    items = db.query(Supplier).order_by(Supplier.name).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(
    body: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    existing = db.execute(select(Supplier).where(Supplier.name == body.name)).scalar_one_or_none()
    if existing:
        raise ApiError(409, "DUPLICATE_NAME", f"Supplier '{body.name}' already exists", field="name")
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    db.flush()
    audit(db, current_user, "SUPPLIER_CREATE", "supplier", supplier.id, {"name": supplier.name})
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "store_manager", "viewer")),
):
    s = db.get(Supplier, supplier_id)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    return s


@router.patch("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    s = db.get(Supplier, supplier_id)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(s, k, v)
    audit(db, current_user, "SUPPLIER_UPDATE", "supplier", supplier_id, updates)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    s = db.get(Supplier, supplier_id)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    audit(db, current_user, "SUPPLIER_DELETE", "supplier", supplier_id, {"name": s.name})
    db.delete(s)
    db.commit()
