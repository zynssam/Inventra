"""
app/routers/products.py — /products endpoints

Includes:
- Paginated list with search, filter, sort, forecast state
- Create (with optional initial_quantity that creates opening adjustment)
- Full detail with embedded forecast + recommendation
- PATCH, archive, restore
- /lookup (QR/SKU/ID)
- /qr-payload
- /products/{id}/transactions
- /products/{id}/usage (daily series)
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, StockTransaction, TxType, User
from app.queries.usage import UsageStats, get_daily_series, get_incoming_stock, get_usage
from app.schemas import (
    Page,
    ProductCreate,
    ProductDetail,
    ProductOut,
    ProductUpdate,
    TransactionOut,
)
from app.services.audit_service import audit
from app.services.forecasting_service import compute_forecast
from app.services.inventory_service import apply_movement
from app.services.reorder_service import compute_reorder
from app.services.settings_service import get_settings

router = APIRouter(prefix="/products", tags=["products"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))
AS = Depends(require_role("admin", "storekeeper"))
ADMIN = Depends(require_role("admin"))

_SORT_MAP = {
    "name": Product.name,
    "sku": Product.sku,
    "current_quantity": Product.current_quantity,
    "unit_cost": Product.unit_cost,
    "updated_at": Product.updated_at,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stock_status(p: Product) -> str:
    if p.current_quantity == 0:
        return "out_of_stock"
    if p.current_quantity <= p.minimum_stock:
        return "low_stock"
    return "healthy"


def _product_out(p: Product, db: Session | None = None, include_forecast: bool = False) -> ProductOut:
    out = ProductOut.model_validate(p)
    out.unit_cost = str(p.unit_cost)
    out.selling_price = str(p.selling_price) if p.selling_price is not None else None
    out.status = _stock_status(p)
    if include_forecast and db:
        settings = get_settings(db)
        usage_map = get_usage(db, [p.id], window_days=settings.usage_window_days)
        u: UsageStats = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=settings.usage_window_days))
        fc = compute_forecast(
            product_id=p.id,
            current_quantity=p.current_quantity,
            total_usage=u.total_usage,
            usage_days=u.usage_days,
            observed_days=u.observed_days,
            window_days=u.window_days,
            daily_series=u.daily_series,
            min_usage_days=settings.min_usage_days,
            warning_days=settings.warning_days,
            critical_days=settings.critical_days,
        )
        out.forecast_state = fc.state
        out.days_until_stockout = fc.days_until_stockout
    return out


# ---------------------------------------------------------------------------
# Routes — NOTE: /lookup and /import-template MUST come before /{id}
# ---------------------------------------------------------------------------

@router.get("/lookup", response_model=ProductOut)
def lookup_product(
    code: str = Query(...),
    db: Session = Depends(get_db),
    _: User = ANY,
):
    """
    QR/SKU lookup: accepts scanned QR payload SS:{sku}, a raw SKU, or a numeric ID.
    """
    product = None
    # Try SS:{sku} payload
    if code.startswith("SS:"):
        sku = code[3:]
        product = db.query(Product).filter(Product.sku == sku).one_or_none()
    elif code.isdigit():
        product = db.get(Product, int(code))
        if product is None:
            product = db.query(Product).filter(Product.sku == code).one_or_none()
    else:
        product = db.query(Product).filter(Product.sku == code).one_or_none()

    if product is None:
        raise ApiError(404, "NOT_FOUND", f"No product found for code '{code}'")
    return _product_out(product, db, include_forecast=True)


@router.get("", response_model=Page[ProductOut])
def list_products(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    sort: str = "name",
    order: str = "asc",
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    query = db.query(Product)
    if not include_archived:
        query = query.filter(Product.is_archived == False)  # noqa: E712
    if q:
        query = query.filter(
            or_(Product.name.ilike(f"%{q}%"), Product.sku.ilike(f"%{q}%"))
        )
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if supplier_id is not None:
        query = query.filter(Product.default_supplier_id == supplier_id)

    # Status filter: compute in Python after fetching (manageable for prototype)
    sort_col = _SORT_MAP.get(sort, Product.name)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    all_products = query.all()

    if status:
        all_products = [p for p in all_products if _stock_status(p) == status]

    total = len(all_products)
    page_items = all_products[(page - 1) * page_size: page * page_size]

    # Batch fetch forecasts
    settings = get_settings(db)
    pid_list = [p.id for p in page_items]
    usage_map = get_usage(db, pid_list, window_days=settings.usage_window_days) if pid_list else {}

    items = []
    for p in page_items:
        out = _product_out(p)
        u = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=settings.usage_window_days))
        fc = compute_forecast(
            product_id=p.id,
            current_quantity=p.current_quantity,
            total_usage=u.total_usage,
            usage_days=u.usage_days,
            observed_days=u.observed_days,
            window_days=u.window_days,
            daily_series=u.daily_series,
            min_usage_days=settings.min_usage_days,
            warning_days=settings.warning_days,
            critical_days=settings.critical_days,
        )
        out.forecast_state = fc.state
        out.days_until_stockout = fc.days_until_stockout
        items.append(out)

    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductDetail, status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    if db.query(Product).filter(Product.sku == body.sku).one_or_none():
        raise ApiError(409, "DUPLICATE_SKU", f"SKU '{body.sku}' already exists", field="sku")

    data = body.model_dump(exclude={"initial_quantity"})
    product = Product(**data)
    db.add(product)
    db.flush()  # get product.id

    audit(db, current_user, "PRODUCT_CREATE", "product", product.id, {"sku": product.sku})

    if body.initial_quantity and body.initial_quantity > 0:
        apply_movement(
            db,
            current_user,
            product.id,
            body.initial_quantity,
            TxType.adjustment,
            "Opening balance",
        )

    db.commit()
    db.refresh(product)
    return _build_detail(product, db, current_user)


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db), current_user: User = ANY):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    return _build_detail(p, db, current_user)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    for field_name, val in body.model_dump(exclude_unset=True).items():
        setattr(p, field_name, val)
    audit(db, current_user, "PRODUCT_UPDATE", "product", p.id)
    db.commit()
    db.refresh(p)
    return _product_out(p, db, include_forecast=True)


@router.delete("/{product_id}", status_code=204)
def archive_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    p.is_archived = True
    audit(db, current_user, "PRODUCT_ARCHIVE", "product", p.id)
    db.commit()


@router.post("/{product_id}/restore", response_model=ProductOut)
def restore_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    p.is_archived = False
    audit(db, current_user, "PRODUCT_RESTORE", "product", p.id)
    db.commit()
    db.refresh(p)
    return _product_out(p)


@router.get("/{product_id}/qr-payload")
def qr_payload(product_id: int, db: Session = Depends(get_db), _: User = ANY):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    return {"payload": f"SS:{p.sku}"}


@router.get("/{product_id}/transactions", response_model=Page[TransactionOut])
def product_transactions(
    product_id: int,
    type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    q = db.query(StockTransaction).filter(StockTransaction.product_id == product_id)
    if type:
        q = q.filter(StockTransaction.type == type)
    if date_from:
        q = q.filter(StockTransaction.created_at >= date_from)
    if date_to:
        q = q.filter(StockTransaction.created_at <= date_to)
    total = q.count()
    items = q.order_by(StockTransaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{product_id}/usage")
def product_usage(
    product_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    series = get_daily_series(db, product_id, days=days)
    return series


# ---------------------------------------------------------------------------
# Helper: build ProductDetail with embedded forecast + recommendation
# ---------------------------------------------------------------------------

def _build_detail(p: Product, db: Session, current_user) -> ProductDetail:
    settings = get_settings(db)
    usage_map = get_usage(db, [p.id], window_days=settings.usage_window_days)
    u: UsageStats = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=settings.usage_window_days))

    fc = compute_forecast(
        product_id=p.id,
        current_quantity=p.current_quantity,
        total_usage=u.total_usage,
        usage_days=u.usage_days,
        observed_days=u.observed_days,
        window_days=u.window_days,
        daily_series=u.daily_series,
        min_usage_days=settings.min_usage_days,
        warning_days=settings.warning_days,
        critical_days=settings.critical_days,
    )

    incoming = get_incoming_stock(db, p.id)
    target_days = p.target_days or settings.default_target_days
    rec = compute_reorder(
        product_id=p.id,
        product_name=p.name,
        sku=p.sku,
        forecast=fc,
        unit_cost=float(p.unit_cost),
        current_quantity=p.current_quantity,
        incoming=incoming,
        target_days=target_days,
        lead_time_days=p.lead_time_days,
        safety_stock=p.safety_stock,
    )

    detail = ProductDetail.model_validate(p)
    detail.unit_cost = str(p.unit_cost)
    detail.selling_price = str(p.selling_price) if p.selling_price is not None else None
    detail.status = _stock_status(p)
    detail.forecast_state = fc.state
    detail.days_until_stockout = fc.days_until_stockout
    detail.forecast = {
        "product_id": fc.product_id,
        "current_quantity": fc.current_quantity,
        "avg_daily_usage": fc.avg_daily_usage,
        "window_days": fc.window_days,
        "usage_days_observed": fc.usage_days_observed,
        "days_until_stockout": fc.days_until_stockout,
        "projected_stockout_date": fc.projected_stockout_date.isoformat() if fc.projected_stockout_date else None,
        "state": fc.state,
        "explanation": fc.explanation,
        "trend": fc.trend,
    }
    detail.recommendation = {
        "reorder_qty": rec.reorder_qty,
        "estimated_cost": rec.estimated_cost,
        "explanation": rec.explanation,
        "inputs": rec.inputs,
        "confidence": rec.confidence,
    }
    return detail
