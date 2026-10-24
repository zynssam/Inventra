"""
app/_temp/queries_stub.py — TEMPORARY stub for Member A's query functions.

⚠️  DELETE THIS FILE once Member A delivers app/queries/{usage,dashboard,reports,insights}.py
    and update the import shims in app/queries/*.py accordingly.

All functions return fixture-shaped data so the backend can be developed and
tested independently. Signatures match team-split.md §4 / architecture.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass
class UsageStats:
    product_id: int
    total_usage: int = 0
    usage_days: int = 0          # distinct days with usage in window
    window_days: int = 14
    observed_days: int = 14      # min(window, days since created)
    avg_daily_usage: float = 0.0
    daily_series: list[dict] = field(default_factory=list)


def get_usage(db, product_ids: list[int], window_days: int = 14) -> dict[int, UsageStats]:
    """
    Stub: returns zero-usage stats for all requested product IDs.
    Real implementation: grouped SQL over stock_transactions for usage types.
    """
    return {
        pid: UsageStats(product_id=pid, window_days=window_days, observed_days=window_days)
        for pid in product_ids
    }


def get_daily_series(db, product_id: int, days: int = 30) -> list[dict]:
    """
    Stub: returns empty daily series.
    Real: [{date, used, received, balance}] for the last `days` days.
    """
    today = date.today()
    return [
        {"date": str(today - timedelta(days=i)), "used": 0, "received": 0, "balance": 0}
        for i in range(days - 1, -1, -1)
    ]


def get_incoming_stock(db, product_id: int) -> int:
    """
    Stub: returns 0 (no open POs).
    Real: Σ (quantity_ordered - quantity_received) for ordered/partially_received POs.
    """
    return 0


# ---------------------------------------------------------------------------
# Dashboard query stubs
# ---------------------------------------------------------------------------

def dashboard_summary(db) -> dict:
    return {
        "total_products": 0,
        "total_units": 0,
        "low_stock_count": 0,
        "out_of_stock_count": 0,
        "total_inventory_value": "0.00",
        "critical_forecast_count": 0,
        "health_score": 100.0,
    }


def movement_chart(db, days: int = 30) -> list[dict]:
    today = date.today()
    return [
        {"date": str(today - timedelta(days=i)), "stock_in": 0, "stock_out": 0}
        for i in range(days - 1, -1, -1)
    ]


def top_used(db, days: int = 30, limit: int = 5) -> list[dict]:
    return []


def category_value(db) -> list[dict]:
    return []


def alerts_base(db) -> list[dict]:
    """Returns raw alert rows; severity is added by the router."""
    return []


# ---------------------------------------------------------------------------
# Report query stubs
# ---------------------------------------------------------------------------

def stock_movements(db, **filters) -> list[dict]:
    return []


def inventory_valuation(db) -> dict:
    return {"items": [], "subtotals": [], "grand_total": "0.00"}


def stock_status(db) -> list[dict]:
    return []
