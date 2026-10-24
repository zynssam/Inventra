"""app/routers/forecasting.py — GET /forecasts and GET /forecasts/{product_id}"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, User
from app.queries.usage import UsageStats, get_usage
from app.schemas import ForecastOut
from app.services.forecasting_service import compute_forecast
from app.services.settings_service import get_settings

router = APIRouter(prefix="/forecasts", tags=["forecasts"])
ANY = Depends(require_role("admin", "store_manager", "viewer"))


def _run_forecast(p: Product, db: Session, window_days: int | None = None) -> ForecastOut:
    settings = get_settings(db)
    w = window_days or settings.usage_window_days
    today = date.today()
    usage_map = get_usage(db, [p.id], window_days=w, today=today)
    u: UsageStats = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=w))
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
    return ForecastOut(
        product_id=fc.product_id,
        product_name=p.name,
        sku=p.sku,
        current_quantity=fc.current_quantity,
        avg_daily_usage=fc.avg_daily_usage,
        window_days=fc.window_days,
        usage_days_observed=fc.usage_days_observed,
        days_until_stockout=fc.days_until_stockout,
        projected_stockout_date=fc.projected_stockout_date,
        state=fc.state,
        explanation=fc.explanation,
        trend=fc.trend,
    )


@router.get("", response_model=list[ForecastOut])
def list_forecasts(
    state: Optional[str] = None,
    window_days: Optional[int] = None,
    sort: str = "days_until_stockout",
    db: Session = Depends(get_db),
    _: User = ANY,
):
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa: E712
    forecasts = [_run_forecast(p, db, window_days) for p in products]
    if state:
        forecasts = [f for f in forecasts if f.state == state]
    if sort == "days_until_stockout":
        forecasts.sort(key=lambda f: (f.days_until_stockout is None, f.days_until_stockout or 0))
    return forecasts


@router.get("/{product_id}", response_model=ForecastOut)
def get_forecast(
    product_id: int,
    window_days: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    p = db.get(Product, product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
    return _run_forecast(p, db, window_days)
