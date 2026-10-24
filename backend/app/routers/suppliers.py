"""
app/routers/suppliers.py — /suppliers endpoints
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, StockTransaction, Supplier, User
from app.schemas import (
    Page,
    ProductOut,
    SupplierCreate,
    SupplierDetail,
    SupplierOut,
    SupplierUpdate,
    TransactionOut,
)
from app.services.audit_service import audit

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))
AS = Depends(require_role("admin", "storekeeper"))
ADMIN = Depends(require_role("admin"))


def _supplier_out(s: Supplier, db: Session) -> SupplierDetail:
    product_count = db.query(Product).filter(Product.default_supplier_id == s.id).count()
    out = SupplierDetail.model_validate(s)
    out.product_count = product_count
    return out


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    q: str | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    query = db.query(Supplier)
    if not include_archived:
        query = query.filter(Supplier.is_archived == False)  # noqa: E712
    if q:
        query = query.filter(Supplier.name.ilike(f"%{q}%"))
    return [SupplierOut.model_validate(s) for s in query.order_by(Supplier.name).all()]


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(
    body: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    sup = Supplier(**body.model_dump())
    db.add(sup)
    db.flush()
    audit(db, current_user, "SUPPLIER_CREATE", "supplier", sup.id, {"name": sup.name})
    db.commit()
    db.refresh(sup)
    return SupplierOut.model_validate(sup)


@router.get("/{supplier_id}", response_model=SupplierDetail)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _: User = ANY):
    sup = db.get(Supplier, supplier_id)
    if sup is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    return _supplier_out(sup, db)


@router.patch("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    sup = db.get(Supplier, supplier_id)
    if sup is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    for field_name, val in body.model_dump(exclude_unset=True).items():
        setattr(sup, field_name, val)
    audit(db, current_user, "SUPPLIER_UPDATE", "supplier", sup.id)
    db.commit()
    db.refresh(sup)
    return SupplierOut.model_validate(sup)


@router.delete("/{supplier_id}", status_code=204)
def archive_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    sup = db.get(Supplier, supplier_id)
    if sup is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    sup.is_archived = True
    audit(db, current_user, "SUPPLIER_ARCHIVE", "supplier", sup.id)
    db.commit()


@router.get("/{supplier_id}/products", response_model=list[ProductOut])
def supplier_products(supplier_id: int, db: Session = Depends(get_db), _: User = ANY):
    sup = db.get(Supplier, supplier_id)
    if sup is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    products = db.query(Product).filter(Product.default_supplier_id == supplier_id).all()
    return [_product_to_out(p) for p in products]


@router.get("/{supplier_id}/transactions", response_model=Page[TransactionOut])
def supplier_transactions(
    supplier_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    sup = db.get(Supplier, supplier_id)
    if sup is None:
        raise ApiError(404, "NOT_FOUND", f"Supplier {supplier_id} not found")
    q = db.query(StockTransaction).filter(StockTransaction.supplier_id == supplier_id)
    total = q.count()
    items = q.order_by(StockTransaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _product_to_out(p: Product) -> ProductOut:
    from app.models import TxType
    status = "out_of_stock" if p.current_quantity == 0 else \
             "low_stock" if p.current_quantity <= p.minimum_stock else "healthy"
    out = ProductOut.model_validate(p)
    out.status = status
    out.unit_cost = str(p.unit_cost)
    out.selling_price = str(p.selling_price) if p.selling_price is not None else None
    return out
