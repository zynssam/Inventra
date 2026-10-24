"""
app/services/forecasting_service.py — usage, forecast, and trend computations.

Formulas from architecture.md §6.2–6.3.

Key rules:
- avg_daily = total_usage / observed_days  (whole window, NOT just active days)
- sufficient_data ⟺ usage_days >= min_usage_days AND total_usage > 0
- days_until_stockout = current_quantity / avg_daily_usage
- trend: compare second half of window usage to first half
- This service is unit-testable with fake UsageStats objects (no DB needed).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


@dataclass
class ForecastResult:
    product_id: int
    current_quantity: int
    avg_daily_usage: Optional[float]
    window_days: int
    usage_days_observed: int
    days_until_stockout: Optional[float]
    projected_stockout_date: Optional[date]
    state: str   # "ok"|"warning"|"critical"|"out_of_stock"|"insufficient_data"|"no_recent_usage"
    explanation: str
    trend: str   # "rising"|"steady"|"falling"


def compute_forecast(
    product_id: int,
    current_quantity: int,
    total_usage: int,
    usage_days: int,
    observed_days: int,
    window_days: int,
    daily_series: list[dict],  # [{date, used, received, balance}] newest last
    min_usage_days: int,
    warning_days: int,
    critical_days: int,
    today: date | None = None,
) -> ForecastResult:
    """
    Pure function — no DB.  All inputs already resolved by the caller.
    Spec examples:
      current=24, total_usage=56 over 14 days (4/day) → days=6.0, state="warning"
    """
    if today is None:
        today = date.today()

    # ------------------------------------------------------------------ #
    # out_of_stock shortcut
    # ------------------------------------------------------------------ #
    if current_quantity == 0:
        return ForecastResult(
            product_id=product_id,
            current_quantity=0,
            avg_daily_usage=None,
            window_days=window_days,
            usage_days_observed=usage_days,
            days_until_stockout=0.0,
            projected_stockout_date=today,
            state="out_of_stock",
            explanation="Product is out of stock.",
            trend=_trend(daily_series, window_days),
        )

    # ------------------------------------------------------------------ #
    # Average daily usage — divide by the WHOLE window (observed_days)
    # ------------------------------------------------------------------ #
    avg_daily = total_usage / observed_days if observed_days > 0 else 0.0

    # ------------------------------------------------------------------ #
    # Sufficient data gate
    # ------------------------------------------------------------------ #
    if total_usage == 0:
        return ForecastResult(
            product_id=product_id,
            current_quantity=current_quantity,
            avg_daily_usage=None,
            window_days=window_days,
            usage_days_observed=usage_days,
            days_until_stockout=None,
            projected_stockout_date=None,
            state="no_recent_usage",
            explanation=f"No usage recorded in the last {window_days} days.",
            trend="steady",
        )

    if usage_days < min_usage_days:
        return ForecastResult(
            product_id=product_id,
            current_quantity=current_quantity,
            avg_daily_usage=round(avg_daily, 4),
            window_days=window_days,
            usage_days_observed=usage_days,
            days_until_stockout=None,
            projected_stockout_date=None,
            state="insufficient_data",
            explanation=(
                f"Only {usage_days} day(s) of usage data in the last {window_days} days "
                f"(need at least {min_usage_days}). Cannot make a reliable forecast."
            ),
            trend=_trend(daily_series, window_days),
        )

    # ------------------------------------------------------------------ #
    # Days until stockout
    # ------------------------------------------------------------------ #
    days_left = current_quantity / avg_daily

    # State
    if days_left <= critical_days:
        state = "critical"
    elif days_left <= warning_days:
        state = "warning"
    else:
        state = "ok"

    projected = today + timedelta(days=days_left)

    explanation = (
        f"{current_quantity} in stock ÷ {round(avg_daily, 1)}/day "
        f"({window_days}-day average) ≈ {round(days_left, 1)} days left."
    )

    return ForecastResult(
        product_id=product_id,
        current_quantity=current_quantity,
        avg_daily_usage=round(avg_daily, 4),
        window_days=window_days,
        usage_days_observed=usage_days,
        days_until_stockout=round(days_left, 4),
        projected_stockout_date=projected,
        state=state,
        explanation=explanation,
        trend=_trend(daily_series, window_days),
    )


def _trend(daily_series: list[dict], window_days: int) -> str:
    """
    Compare usage in the later half of the window to the earlier half.
    Returns "rising" | "steady" | "falling".
    """
    if not daily_series:
        return "steady"

    series = daily_series[-window_days:]  # at most window_days entries
    half = max(1, len(series) // 2)
    first_half = sum(d.get("used", 0) for d in series[:half])
    second_half = sum(d.get("used", 0) for d in series[half:])

    if first_half == 0 and second_half == 0:
        return "steady"
    if first_half == 0:
        return "rising"

    ratio = second_half / first_half
    if ratio > 1.2:
        return "rising"
    elif ratio < 0.8:
        return "falling"
    return "steady"
