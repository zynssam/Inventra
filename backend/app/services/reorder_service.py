"""
app/services/reorder_service.py — reorder quantity and explanation engine.

Formula from architecture.md §6.4:
  target_stock  = avg_daily × (coverage_days + lead_time_days) + safety_stock
  incoming      = Σ open PO (ordered − received)
  reorder_qty   = max(0, ceil(target_stock − current_quantity − incoming))

Spec example (must pass test):
  usage 5/day, target 20 d, stock 12, incoming 10, lead=0, safety=0
  → max(0, 5×20 − 12 − 10) = 78

Confidence:
  high   ≥ 7 usage_days in window
  medium 3–6
  low    otherwise (returned with note, still computed unless insufficient_data)

This service is unit-testable with fake inputs (no DB).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.services.forecasting_service import ForecastResult


@dataclass
class ReorderResult:
    product_id: int
    product_name: str
    sku: str
    reorder_qty: int
    estimated_cost: str          # str("Decimal")
    explanation: str
    inputs: dict
    confidence: str
    forecast_state: str


def compute_reorder(
    product_id: int,
    product_name: str,
    sku: str,
    forecast: ForecastResult,
    unit_cost: float,
    current_quantity: int,
    incoming: int,
    target_days: int,
    lead_time_days: int = 0,
    safety_stock: int = 0,
) -> ReorderResult:
    """
    Pure function.  Returns a ReorderResult regardless of forecast state
    (the router filters out insufficient_data products when building the list).
    """
    avg_daily = forecast.avg_daily_usage or 0.0
    window_days = forecast.window_days
    usage_days = forecast.usage_days_observed
    state = forecast.state

    # ------------------------------------------------------------------ #
    # Confidence
    # ------------------------------------------------------------------ #
    if usage_days >= 7:
        confidence = "high"
    elif usage_days >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # ------------------------------------------------------------------ #
    # Reorder quantity
    # ------------------------------------------------------------------ #
    target_stock = avg_daily * (target_days + lead_time_days) + safety_stock
    raw_reorder = target_stock - current_quantity - incoming
    reorder_qty = max(0, math.ceil(raw_reorder))

    cost = Decimal(str(round(reorder_qty * unit_cost, 2)))
    # Strip trailing zeros but avoid scientific notation (e.g. 7.8E+2)
    estimated_cost = format(cost.normalize(), 'f')

    # ------------------------------------------------------------------ #
    # Explanation
    # ------------------------------------------------------------------ #
    needs = round(avg_daily * target_days, 1) if lead_time_days == 0 and safety_stock == 0 else \
        round(avg_daily * (target_days + lead_time_days) + safety_stock, 1)

    if state in ("insufficient_data", "no_recent_usage"):
        explanation = (
            f"Insufficient usage data ({usage_days} day(s) observed). "
            f"Cannot compute a reliable recommendation."
        )
    else:
        explanation = (
            f"Uses {round(avg_daily, 1)}/day over the last {window_days} days. "
            f"For {target_days} days of cover you need {int(round(avg_daily * target_days))} units. "
            f"You have {current_quantity} on hand and {incoming} on order, so order {reorder_qty}."
        )
        if lead_time_days > 0:
            explanation += f" (Lead time: {lead_time_days} days.)"
        if safety_stock > 0:
            explanation += f" (Safety stock: {safety_stock} units.)"
        if confidence == "low":
            explanation += " ⚠ Limited data — treat as an estimate."

    inputs = {
        "avg_daily_usage": round(avg_daily, 4),
        "window_days": window_days,
        "target_days": target_days,
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
        "current": current_quantity,
        "incoming": incoming,
    }

    return ReorderResult(
        product_id=product_id,
        product_name=product_name,
        sku=sku,
        reorder_qty=reorder_qty,
        estimated_cost=estimated_cost,
        explanation=explanation,
        inputs=inputs,
        confidence=confidence,
        forecast_state=state,
    )
