"""
app/routers/dashboard.py — /dashboard/* endpoints

Calls the query layer (Member A) for aggregated data, then adds:
- health score formula (architecture.md §6.7)
- alert severity from forecast state
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Product, StockTransaction, User
from app.queries.dashboard import (
    alerts_base,
    category_value,
    dashboard_summary,
    movement_chart,
    top_used,
)
from app.queries.usage import UsageStats, get_usage
from app.schemas import AlertOut, DashboardSummary
from app.services.forecasting_service import compute_forecast
from app.services.settings_service import get_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _: User = ANY):
    """
    Computes summary stats directly from the product table and adds
    the health score (§6.7) and critical forecast count.
    The query layer stub is called but real data is computed here
    so the endpoint is functional even before Member A delivers dashboard.py.
    """
    products = db.query(Product).filter(Product.is_archived == False).all()  # noqa: E712
    total_products = len(products)
    healthy = sum(1 for p in products if p.current_quantity > p.minimum_stock)
    low_stock = sum(1 for p in products if 0 < p.current_quantity <= p.minimum_stock)
    out_of_stock = sum(1 for p in products if p.current_quantity == 0)
    total_units = sum(p.current_quantity for p in products)
    total_value = sum(float(p.unit_cost) * p.current_quantity for p in products)

    # Health score: 100 × (healthy + 0.5 × low) / total  (§6.7)
    if total_products > 0:
        health_score = round(100 * (healthy + 0.5 * low_stock) / total_products, 1)
    else:
        health_score = 100.0

    # Critical forecast count
    settings = get_settings(db)
    pids = [p.id for p in products]
    usage_map = get_usage(db, pids, window_days=settings.usage_window_days) if pids else {}
    critical_count = 0
    for p in products:
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
        if fc.state == "critical":
            critical_count += 1

    return DashboardSummary(
        total_products=total_products,
        total_units=total_units,
        low_stock_count=low_stock,
        out_of_stock_count=out_of_stock,
        total_inventory_value=str(round(total_value, 2)),
        critical_forecast_count=critical_count,
        health_score=health_score,
    )


@router.get("/movement-chart")
def movement_chart_endpoint(
    days: int = 30,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    """
    Returns [{date, stock_in, stock_out}] for the last `days` days.
    Falls back to direct DB query if the query layer stub returns zeros.
    """
    # Build from DB directly (so it works without Member A's SQL)
    today = date.today()
    start = today - timedelta(days=days - 1)
    txs = (
        db.query(StockTransaction)
        .filter(StockTransaction.created_at >= start)
        .all()
    )
    day_map: dict[str, dict] = {
        str(today - timedelta(days=i)): {"date": str(today - timedelta(days=i)), "stock_in": 0, "stock_out": 0}
        for i in range(days - 1, -1, -1)
    }
    for tx in txs:
        d = tx.created_at.strftime("%Y-%m-%d")
        if d in day_map:
            if tx.quantity_delta > 0:
                day_map[d]["stock_in"] += tx.quantity_delta
            else:
                day_map[d]["stock_out"] += abs(tx.quantity_delta)
    return list(day_map.values())


@router.get("/top-used")
def top_used_endpoint(
    days: int = 30,
    limit: int = 5,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    result = top_used(db, days=days, limit=limit)
    if result:
        return result
    # Fallback: compute from DB
    from app.models import TxType as TX
    today = date.today()
    start = today - timedelta(days=days)
    USAGE_TYPES = {TX.sale.value, TX.issue.value, TX.consumption.value}
    txs = (
        db.query(StockTransaction)
        .filter(
            StockTransaction.created_at >= start,
            StockTransaction.type.in_(USAGE_TYPES),
        )
        .all()
    )
    usage_by_product: dict[int, int] = {}
    for tx in txs:
        pid = tx.product_id
        usage_by_product[pid] = usage_by_product.get(pid, 0) + abs(tx.quantity_delta)
    sorted_pids = sorted(usage_by_product, key=lambda k: usage_by_product[k], reverse=True)[:limit]
    rows = []
    for pid in sorted_pids:
        p = db.get(Product, pid)
        if p:
            rows.append({"product_id": pid, "product_name": p.name, "sku": p.sku, "total_used": usage_by_product[pid]})
    return rows


@router.get("/alerts", response_model=list[AlertOut])
def alerts(db: Session = Depends(get_db), _: User = ANY):
    """
    Returns out-of-stock, low-stock, and critical-forecast products with severity.
    """
    settings = get_settings(db)
    products = db.query(Product).filter(Product.is_archived == False).all()  # noqa: E712
    pids = [p.id for p in products]
    usage_map = get_usage(db, pids, window_days=settings.usage_window_days) if pids else {}

    result = []
    for p in products:
        alerts_list = []
        if p.current_quantity == 0:
            alerts_list.append(AlertOut(
                product_id=p.id,
                product_name=p.name,
                sku=p.sku,
                current_quantity=p.current_quantity,
                severity="critical",
                alert_type="out_of_stock",
                message=f"{p.name} is out of stock.",
            ))
        elif p.current_quantity <= p.minimum_stock:
            alerts_list.append(AlertOut(
                product_id=p.id,
                product_name=p.name,
                sku=p.sku,
                current_quantity=p.current_quantity,
                severity="warning",
                alert_type="low_stock",
                message=f"{p.name} is below minimum stock ({p.minimum_stock}).",
            ))
        else:
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
            if fc.state in ("critical", "warning"):
                severity = "critical" if fc.state == "critical" else "warning"
                alerts_list.append(AlertOut(
                    product_id=p.id,
                    product_name=p.name,
                    sku=p.sku,
                    current_quantity=p.current_quantity,
                    severity=severity,
                    alert_type="forecast",
                    message=fc.explanation,
                ))
        result.extend(alerts_list)

    result.sort(key=lambda a: {"critical": 0, "warning": 1}.get(a.severity, 2))
    return result


@router.get("/recent-transactions")
def recent_transactions(
    limit: int = 10,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    txs = (
        db.query(StockTransaction)
        .order_by(StockTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for tx in txs:
        p = db.get(Product, tx.product_id)
        result.append({
            "id": tx.id,
            "product_id": tx.product_id,
            "product_name": p.name if p else None,
            "sku": p.sku if p else None,
            "type": tx.type.value,
            "quantity_delta": tx.quantity_delta,
            "balance_after": tx.balance_after,
            "reason": tx.reason,
            "created_at": tx.created_at.isoformat(),
        })
    return result


@router.get("/category-value")
def category_value_endpoint(db: Session = Depends(get_db), _: User = ANY):
    result = category_value(db)
    if result:
        return result
    # Fallback: compute from DB
    from app.models import Category
    categories = db.query(Category).all()
    rows = []
    for cat in categories:
        products = db.query(Product).filter(
            Product.category_id == cat.id,
            Product.is_archived == False,  # noqa: E712
        ).all()
        value = sum(float(p.unit_cost) * p.current_quantity for p in products)
        rows.append({"category_id": cat.id, "category_name": cat.name, "total_value": str(round(value, 2))})
    # Products with no category
    uncategorized = db.query(Product).filter(
        Product.category_id == None,  # noqa: E711
        Product.is_archived == False,  # noqa: E712
    ).all()
    if uncategorized:
        value = sum(float(p.unit_cost) * p.current_quantity for p in uncategorized)
        rows.append({"category_id": None, "category_name": "Uncategorized", "total_value": str(round(value, 2))})
    return rows
