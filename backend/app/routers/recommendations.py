"""
app/routers/recommendations.py — /recommendations endpoints + /simulate
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, User
from app.queries.usage import UsageStats, get_incoming_stock, get_usage
from app.schemas import (
    RecommendationInputs,
    RecommendationListOut,
    RecommendationOut,
    SimulateRequest,
)
from app.services.forecasting_service import compute_forecast
from app.services.reorder_service import compute_reorder
from app.services.settings_service import get_settings

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))
AS = Depends(require_role("admin", "storekeeper"))


def _run_recommendation(
    p: Product,
    db: Session,
    target_days: int,
    window_days: int,
    min_usage_days: int,
    warning_days: int,
    critical_days: int,
    lead_time_days: int | None = None,
    safety_stock: int | None = None,
) -> RecommendationOut | None:
    usage_map = get_usage(db, [p.id], window_days=window_days)
    u: UsageStats = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=window_days))
    fc = compute_forecast(
        product_id=p.id,
        current_quantity=p.current_quantity,
        total_usage=u.total_usage,
        usage_days=u.usage_days,
        observed_days=u.observed_days,
        window_days=u.window_days,
        daily_series=u.daily_series,
        min_usage_days=min_usage_days,
        warning_days=warning_days,
        critical_days=critical_days,
    )
    incoming = get_incoming_stock(db, p.id)
    eff_lead = lead_time_days if lead_time_days is not None else p.lead_time_days
    eff_safety = safety_stock if safety_stock is not None else p.safety_stock

    rec = compute_reorder(
        product_id=p.id,
        product_name=p.name,
        sku=p.sku,
        forecast=fc,
        unit_cost=float(p.unit_cost),
        current_quantity=p.current_quantity,
        incoming=incoming,
        target_days=target_days,
        lead_time_days=eff_lead,
        safety_stock=eff_safety,
    )
    return RecommendationOut(
        product_id=rec.product_id,
        product_name=rec.product_name,
        sku=rec.sku,
        reorder_qty=rec.reorder_qty,
        estimated_cost=rec.estimated_cost,
        explanation=rec.explanation,
        inputs=RecommendationInputs(**rec.inputs),
        confidence=rec.confidence,
        forecast_state=rec.forecast_state,
    )


@router.get("", response_model=RecommendationListOut)
def list_recommendations(
    target_days: Optional[int] = None,
    window_days: Optional[int] = None,
    supplier_id: Optional[int] = None,
    category_id: Optional[int] = None,
    include_all: bool = False,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    settings = get_settings(db)
    t_days = target_days or settings.default_target_days
    w_days = window_days or settings.usage_window_days

    query = db.query(Product).filter(Product.is_archived == False)  # noqa: E712
    if supplier_id is not None:
        query = query.filter(Product.default_supplier_id == supplier_id)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    products = query.all()
    items = []
    for p in products:
        rec = _run_recommendation(
            p, db, t_days, w_days,
            settings.min_usage_days, settings.warning_days, settings.critical_days,
        )
        if rec and (include_all or rec.reorder_qty > 0):
            items.append(rec)

    total_cost = str(Decimal(sum(Decimal(r.estimated_cost) for r in items)))
    return RecommendationListOut(items=items, total_estimated_cost=total_cost)


@router.post("/simulate", response_model=RecommendationListOut)
def simulate(
    body: SimulateRequest,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    settings = get_settings(db)
    w_days = body.window_days or settings.usage_window_days
    products = db.query(Product).filter(Product.is_archived == False).all()  # noqa: E712

    items = []
    for p in products:
        rec = _run_recommendation(
            p, db, body.target_days, w_days,
            settings.min_usage_days, settings.warning_days, settings.critical_days,
            lead_time_days=body.lead_time_days,
            safety_stock=body.safety_days,
        )
        if rec and rec.reorder_qty > 0:
            items.append(rec)

    total_cost = str(Decimal(sum(Decimal(r.estimated_cost) for r in items)))
    return RecommendationListOut(items=items, total_estimated_cost=total_cost)


@router.get("/{product_id}", response_model=RecommendationOut)
def get_recommendation(
    product_id: int,
    target_days: Optional[int] = None,
    window_days: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    settings = get_settings(db)
    t_days = target_days or (p.target_days or settings.default_target_days)
    w_days = window_days or settings.usage_window_days
    return _run_recommendation(
        p, db, t_days, w_days,
        settings.min_usage_days, settings.warning_days, settings.critical_days,
    )
