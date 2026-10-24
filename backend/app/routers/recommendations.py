"""app/routers/recommendations.py — /recommendations and /simulate"""
from decimal import Decimal
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, User
from app.queries.usage import UsageStats, get_usage, get_incoming_stock
from app.schemas import (
    RecommendationInputs, RecommendationListOut, RecommendationOut, SimulateRequest,
)
from app.services.forecasting_service import compute_forecast
from app.services.reorder_service import compute_reorder
from app.services.settings_service import get_settings

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _run_recommendation(p, db, t_days, w_days, settings, lead_time_days=None, safety_stock=None):
    today = date.today()
    usage_map = get_usage(db, [p.id], window_days=w_days, today=today)
    u = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=w_days))
    fc = compute_forecast(
        product_id=p.id, current_quantity=p.current_quantity,
        total_usage=u.total_usage, usage_days=u.usage_days,
        observed_days=u.observed_days, window_days=u.window_days,
        daily_series=u.daily_series, min_usage_days=settings.min_usage_days,
        warning_days=settings.warning_days, critical_days=settings.critical_days,
    )
    incoming = get_incoming_stock(db, p.id)
    rec = compute_reorder(
        product_id=p.id, product_name=p.name, sku=p.sku, forecast=fc,
        unit_cost=float(p.unit_cost), current_quantity=p.current_quantity,
        incoming=incoming, target_days=t_days,
        lead_time_days=lead_time_days if lead_time_days is not None else p.min_order_qty,
        safety_stock=safety_stock or 0,
    )
    return RecommendationOut(
        product_id=rec.product_id, product_name=rec.product_name, sku=rec.sku,
        reorder_qty=rec.reorder_qty, estimated_cost=rec.estimated_cost,
        explanation=rec.explanation, inputs=RecommendationInputs(**rec.inputs),
        confidence=rec.confidence, forecast_state=rec.forecast_state,
    )


@router.get("", response_model=RecommendationListOut)
def list_recommendations(
    target_days: Optional[int] = None,
    window_days: Optional[int] = None,
    supplier_id: Optional[int] = None,
    category_id: Optional[int] = None,
    include_all: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "store_manager", "viewer")),
):
    settings = get_settings(db)
    t_days = target_days or settings.default_target_days
    w_days = window_days or settings.usage_window_days
    q = db.query(Product).filter(Product.is_active == True)  # noqa
    if supplier_id:
        q = q.filter(Product.supplier_id == supplier_id)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    items = []
    for p in q.all():
        rec = _run_recommendation(p, db, t_days, w_days, settings)
        if include_all or rec.reorder_qty > 0:
            items.append(rec)
    total_cost = format(Decimal(sum(Decimal(r.estimated_cost) for r in items)).normalize(), 'f')
    return RecommendationListOut(items=items, total_estimated_cost=total_cost)


@router.post("/simulate", response_model=RecommendationListOut)
def simulate(
    body: SimulateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "store_manager", "viewer")),
):
    settings = get_settings(db)
    w_days = body.window_days or settings.usage_window_days
    items = []
    for p in db.query(Product).filter(Product.is_active == True).all():  # noqa
        rec = _run_recommendation(
            p, db, body.target_days, w_days, settings,
            lead_time_days=body.lead_time_days, safety_stock=body.safety_days,
        )
        if rec.reorder_qty > 0:
            items.append(rec)
    total_cost = format(Decimal(sum(Decimal(r.estimated_cost) for r in items)).normalize(), 'f')
    return RecommendationListOut(items=items, total_estimated_cost=total_cost)


@router.get("/{product_id}", response_model=RecommendationOut)
def get_recommendation(
    product_id: int,
    target_days: Optional[int] = None,
    window_days: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "store_manager", "viewer")),
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    settings = get_settings(db)
    t_days = target_days or settings.default_target_days
    w_days = window_days or settings.usage_window_days
    return _run_recommendation(p, db, t_days, w_days, settings)
