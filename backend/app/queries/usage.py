"""
app/queries/usage.py — wraps Member A's database/usage.py.

Member A's signature:
  get_usage(db, product_ids, window_days, today) -> dict[int, UsageStats]
  get_incoming_stock(db, product_ids) -> dict[int, int]

UsageStats fields: total_usage, usage_days, first_activity_date,
                   recent_half_usage, earlier_half_usage

We adapt these to the shape expected by our forecasting service.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session


@dataclass
class UsageStats:
    """Adapter dataclass matching what forecasting_service.compute_forecast expects."""
    product_id: int
    total_usage: int = 0
    usage_days: int = 0
    window_days: int = 30
    observed_days: int = 1
    avg_daily_usage: float = 0.0
    daily_series: list = None
    first_activity_date: Optional[date] = None
    recent_half_usage: int = 0
    earlier_half_usage: int = 0

    def __post_init__(self):
        if self.daily_series is None:
            self.daily_series = []
        if self.avg_daily_usage == 0.0 and self.observed_days > 0:
            self.avg_daily_usage = self.total_usage / self.observed_days


def get_usage(
    db: Session,
    product_ids: list[int],
    window_days: int,
    today: Optional[date] = None,
) -> dict[int, UsageStats]:
    """
    Call Member A's get_usage and adapt to our UsageStats dataclass.
    Falls back to empty stats if Member A's SQL fails (e.g., SQLite in tests).
    """
    from datetime import date as date_cls
    today = today or date_cls.today()

    try:
        from database.usage import get_usage as _get_usage  # Member A's real function
        raw = _get_usage(db, product_ids if product_ids else None, window_days, today)
        result = {}
        for pid, r in raw.items():
            observed = max(window_days, 1)
            result[pid] = UsageStats(
                product_id=pid,
                total_usage=r.total_usage,
                usage_days=r.usage_days,
                window_days=window_days,
                observed_days=observed,
                avg_daily_usage=r.total_usage / observed,
                first_activity_date=r.first_activity_date,
                recent_half_usage=r.recent_half_usage,
                earlier_half_usage=r.earlier_half_usage,
            )
        return result
    except Exception:
        # Fallback: compute from DB directly (SQLite / dev mode)
        return _fallback_usage(db, product_ids, window_days, today)


def _fallback_usage(db, product_ids, window_days, today) -> dict[int, UsageStats]:
    """Direct DB fallback for SQLite and pre-Postgres environments."""
    from datetime import timedelta
    from sqlalchemy import func, select
    from app.models import StockTransaction

    start = today - __import__("datetime").timedelta(days=window_days)
    OUT_TYPES = {"stock_out", "stocktake"}

    q = db.query(
        StockTransaction.product_id,
        func.count(func.distinct(
            func.date(StockTransaction.created_at)
        )).label("usage_days"),
        func.coalesce(func.sum(-StockTransaction.quantity_delta), 0).label("total_usage"),
    ).filter(
        StockTransaction.txn_type.in_(OUT_TYPES),
        StockTransaction.quantity_delta < 0,
        StockTransaction.created_at >= start,
    )
    if product_ids:
        q = q.filter(StockTransaction.product_id.in_(product_ids))
    q = q.group_by(StockTransaction.product_id)

    result = {}
    for row in q.all():
        result[row.product_id] = UsageStats(
            product_id=row.product_id,
            total_usage=int(row.total_usage),
            usage_days=int(row.usage_days),
            window_days=window_days,
            observed_days=max(window_days, 1),
            avg_daily_usage=int(row.total_usage) / max(window_days, 1),
        )
    return result


def get_incoming_stock(db: Session, product_id: int) -> int:
    """Return total incoming quantity for a single product (open POs)."""
    try:
        from database.usage import get_incoming_stock as _get_incoming
        result = _get_incoming(db, [product_id])
        return result.get(product_id, 0)
    except Exception:
        return _fallback_incoming(db, product_id)


def _fallback_incoming(db, product_id: int) -> int:
    from app.models import PurchaseOrder, PurchaseOrderItem
    from sqlalchemy import func
    row = db.query(
        func.coalesce(
            func.sum(PurchaseOrderItem.quantity_ordered - PurchaseOrderItem.quantity_received), 0
        )
    ).join(
        PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id
    ).filter(
        PurchaseOrderItem.product_id == product_id,
        PurchaseOrder.status.in_(["ordered", "partially_received"]),
    ).scalar()
    return int(row or 0)


def get_daily_series(db: Session, product_id: int, days: int) -> list[dict]:
    try:
        from database.usage import get_daily_series as _get_ds
        return _get_ds(db, product_id, days)
    except Exception:
        return []
