"""app/routers/dashboard.py — /dashboard/* endpoints"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Product, StockTransaction, User
from app.queries.dashboard import alerts_base, category_value, movement_chart, top_used
from app.queries.usage import UsageStats, get_usage
from app.schemas import AlertOut, DashboardSummary
from app.services.forecasting_service import compute_forecast
from app.services.settings_service import get_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
ANY = Depends(require_role("admin", "store_manager", "viewer"))


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _: User = ANY):
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa
    total_products = len(products)
    healthy  = sum(1 for p in products if p.current_quantity > p.reorder_point)
    low_stock = sum(1 for p in products if 0 < p.current_quantity <= p.reorder_point)
    out_of_stock = sum(1 for p in products if p.current_quantity == 0)
    total_units  = sum(p.current_quantity for p in products)
    total_value  = sum(float(p.unit_cost) * p.current_quantity for p in products)

    health_score = round(100 * (healthy + 0.5 * low_stock) / total_products, 1) if total_products else 100.0

    settings = get_settings(db)
    today = date.today()
    pids = [p.id for p in products]
    usage_map = get_usage(db, pids, window_days=settings.usage_window_days, today=today) if pids else {}
    critical_count = 0
    for p in products:
        u = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=settings.usage_window_days))
        fc = compute_forecast(
            product_id=p.id, current_quantity=p.current_quantity,
            total_usage=u.total_usage, usage_days=u.usage_days,
            observed_days=u.observed_days, window_days=u.window_days,
            daily_series=u.daily_series, min_usage_days=settings.min_usage_days,
            warning_days=settings.warning_days, critical_days=settings.critical_days,
        )
        if fc.state == "critical":
            critical_count += 1

    return DashboardSummary(
        total_products=total_products, total_units=total_units,
        low_stock_count=low_stock, out_of_stock_count=out_of_stock,
        total_inventory_value=str(round(total_value, 2)),
        critical_forecast_count=critical_count, health_score=health_score,
    )


@router.get("/movement-chart")
def movement_chart_endpoint(days: int = 30, db: Session = Depends(get_db), _: User = ANY):
    result = movement_chart(db, days)
    if result:
        return result
    # Fallback for SQLite
    today = date.today()
    day_map = {
        str(today - timedelta(days=i)): {"date": str(today - timedelta(days=i)), "stock_in": 0, "stock_out": 0}
        for i in range(days - 1, -1, -1)
    }
    for tx in db.query(StockTransaction).filter(StockTransaction.created_at >= today - timedelta(days=days)).all():
        d = tx.created_at.strftime("%Y-%m-%d")
        if d in day_map:
            if tx.quantity_delta > 0:
                day_map[d]["stock_in"] += tx.quantity_delta
            else:
                day_map[d]["stock_out"] += abs(tx.quantity_delta)
    return list(day_map.values())


@router.get("/top-used")
def top_used_endpoint(days: int = 30, limit: int = 5, db: Session = Depends(get_db), _: User = ANY):
    result = top_used(db, days=days, limit=limit)
    if result:
        return result
    # Fallback for SQLite
    today = date.today()
    OUT_TYPES = {"stock_out", "stocktake"}
    txs = db.query(StockTransaction).filter(
        StockTransaction.created_at >= today - timedelta(days=days),
        StockTransaction.txn_type.in_(OUT_TYPES),
    ).all()
    usage_by: dict[int, int] = {}
    for tx in txs:
        usage_by[tx.product_id] = usage_by.get(tx.product_id, 0) + abs(tx.quantity_delta)
    rows = []
    for pid in sorted(usage_by, key=lambda k: usage_by[k], reverse=True)[:limit]:
        p = db.get(Product, pid)
        if p:
            rows.append({"product_id": pid, "name": p.name, "sku": p.sku, "used": usage_by[pid]})
    return rows


@router.get("/alerts", response_model=list[AlertOut])
def alerts(db: Session = Depends(get_db), _: User = ANY):
    settings = get_settings(db)
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa
    pids = [p.id for p in products]
    usage_map = get_usage(db, pids, window_days=settings.usage_window_days, today=date.today()) if pids else {}

    result = []
    for p in products:
        if p.current_quantity == 0:
            result.append(AlertOut(
                product_id=p.id, product_name=p.name, sku=p.sku,
                current_quantity=p.current_quantity, severity="critical",
                alert_type="out_of_stock", message=f"{p.name} is out of stock.",
            ))
        elif p.current_quantity <= p.reorder_point:
            result.append(AlertOut(
                product_id=p.id, product_name=p.name, sku=p.sku,
                current_quantity=p.current_quantity, severity="warning",
                alert_type="low_stock",
                message=f"{p.name} is below reorder point ({p.reorder_point}).",
            ))
        else:
            u = usage_map.get(p.id, UsageStats(product_id=p.id, window_days=settings.usage_window_days))
            fc = compute_forecast(
                product_id=p.id, current_quantity=p.current_quantity,
                total_usage=u.total_usage, usage_days=u.usage_days,
                observed_days=u.observed_days, window_days=u.window_days,
                daily_series=u.daily_series, min_usage_days=settings.min_usage_days,
                warning_days=settings.warning_days, critical_days=settings.critical_days,
            )
            if fc.state in ("critical", "warning"):
                result.append(AlertOut(
                    product_id=p.id, product_name=p.name, sku=p.sku,
                    current_quantity=p.current_quantity,
                    severity="critical" if fc.state == "critical" else "warning",
                    alert_type="forecast", message=fc.explanation,
                ))
    result.sort(key=lambda a: {"critical": 0, "warning": 1}.get(a.severity, 2))
    return result


@router.get("/recent-transactions")
def recent_transactions(limit: int = 10, db: Session = Depends(get_db), _: User = ANY):
    txs = db.query(StockTransaction).order_by(StockTransaction.created_at.desc()).limit(limit).all()
    return [
        {
            "id": tx.id, "product_id": tx.product_id,
            "txn_type": tx.txn_type, "quantity_delta": tx.quantity_delta,
            "balance_after": tx.balance_after, "reason": tx.reason,
            "created_at": tx.created_at.isoformat(),
        }
        for tx in txs
    ]


@router.get("/category-value")
def category_value_endpoint(db: Session = Depends(get_db), _: User = ANY):
    result = category_value(db)
    if result:
        return result
    # Fallback for SQLite
    from app.models import Category
    rows = []
    for cat in db.query(Category).all():
        products = db.query(Product).filter(Product.category_id == cat.id, Product.is_active == True).all()  # noqa
        value = sum(float(p.unit_cost) * p.current_quantity for p in products)
        rows.append({"category": cat.name, "value": str(round(value, 2))})
    return rows
