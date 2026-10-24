"""app/routers/products.py — /products CRUD with stock status + forecast state"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, StockTransaction, User
from app.queries.usage import get_usage
from app.schemas import ProductCreate, ProductDetail, ProductOut, ProductUpdate, Page
from app.services.audit_service import audit
from app.services.forecasting_service import compute_forecast
from app.services.inventory_service import apply_movement
from app.services.settings_service import get_settings

router = APIRouter(prefix="/products", tags=["products"])

ANY = Depends(require_role("admin", "store_manager", "viewer"))
AS = Depends(require_role("admin", "store_manager"))
ADMIN = Depends(require_role("admin"))

from datetime import date as date_type


def _status(p: Product) -> str:
    if p.current_quantity == 0:
        return "out_of_stock"
    if p.current_quantity <= p.reorder_point:
        return "low_stock"
    return "healthy"


def _build_detail(p: Product, db: Session, current_user: User) -> ProductDetail:
    out = ProductDetail.model_validate(p)
    out.status = _status(p)
    return out


@router.get("", response_model=Page[ProductOut])
def list_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    is_active: bool = True,
    page: int = 1,
    page_size: int = 20,
    sort: str = "name",
    db: Session = Depends(get_db),
    _: User = ANY,
):
    q = db.query(Product).filter(Product.is_active == is_active)
    if search:
        q = q.filter(
            Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%")
        )
    if category_id is not None:
        q = q.filter(Product.category_id == category_id)
    if supplier_id is not None:
        q = q.filter(Product.supplier_id == supplier_id)

    sort_map = {
        "name": Product.name, "sku": Product.sku,
        "current_quantity": Product.current_quantity,
        "unit_cost": Product.unit_cost,
    }
    q = q.order_by(sort_map.get(sort, Product.name))

    total = q.count()
    products = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for p in products:
        out = ProductOut.model_validate(p)
        out.status = _status(p)
        if status and out.status != status:
            continue
        items.append(out)

    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductDetail, status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    existing = db.execute(select(Product).where(Product.sku == body.sku)).scalar_one_or_none()
    if existing:
        raise ApiError(409, "DUPLICATE_SKU", f"SKU '{body.sku}' already exists", field="sku")

    product = Product(
        name=body.name,
        sku=body.sku,
        category_id=body.category_id,
        supplier_id=body.supplier_id,
        unit=body.unit,
        unit_cost=body.unit_cost,
        reorder_point=body.reorder_point,
        min_order_qty=body.min_order_qty,
        current_quantity=0,
    )
    db.add(product)
    db.flush()

    if body.initial_quantity and body.initial_quantity > 0:
        apply_movement(
            db=db,
            product_id=product.id,
            delta=body.initial_quantity,
            tx_type="stock_in",
            user_id=current_user.id,
            reason="Initial stock",
        )

    audit(db, current_user, "PRODUCT_CREATE", "product", product.id, {"sku": product.sku})
    db.commit()
    db.refresh(product)
    return _build_detail(product, db, current_user)


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    out = ProductDetail.model_validate(p)
    out.status = _status(p)
    return out


@router.patch("/{product_id}", response_model=ProductDetail)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(p, k, v)

    audit(db, current_user, "PRODUCT_UPDATE", "product", product_id, updates)
    db.commit()
    db.refresh(p)
    return _build_detail(p, db, current_user)


@router.delete("/{product_id}", status_code=204)
def archive_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    p.is_active = False
    audit(db, current_user, "PRODUCT_ARCHIVE", "product", product_id, {"sku": p.sku})
    db.commit()
