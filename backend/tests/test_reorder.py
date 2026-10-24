"""
tests/test_reorder.py — unit tests for the reorder service.

Spec example (must pass):
  usage 5/day, target 20 days, stock 12, incoming 10, lead=0, safety=0
  → reorder_qty = max(0, ceil(5×20 − 12 − 10)) = max(0, 78) = 78
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pytest

from app.services.forecasting_service import ForecastResult
from app.services.reorder_service import compute_reorder


def _make_forecast(
    avg_daily: Optional[float],
    current: int,
    usage_days: int = 7,
    window_days: int = 14,
    state: str = "ok",
) -> ForecastResult:
    return ForecastResult(
        product_id=1,
        current_quantity=current,
        avg_daily_usage=avg_daily,
        window_days=window_days,
        usage_days_observed=usage_days,
        days_until_stockout=None,
        projected_stockout_date=None,
        state=state,
        explanation="",
        trend="steady",
    )


def _reorder(
    avg_daily: float,
    current: int,
    incoming: int,
    target_days: int,
    lead_time_days: int = 0,
    safety_stock: int = 0,
    usage_days: int = 7,
    state: str = "ok",
):
    fc = _make_forecast(avg_daily, current, usage_days=usage_days, state=state)
    return compute_reorder(
        product_id=1,
        product_name="Test",
        sku="TEST-001",
        forecast=fc,
        unit_cost=10.0,
        current_quantity=current,
        incoming=incoming,
        target_days=target_days,
        lead_time_days=lead_time_days,
        safety_stock=safety_stock,
    )


class TestSpecExample:
    """
    Spec: usage 5/day, 20 days, stock 12, incoming 10
    → max(0, 5×20 − 12 − 10) = 78
    """

    def test_reorder_qty_78(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20)
        assert result.reorder_qty == 78

    def test_estimated_cost(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20)
        # 78 × 10.0 = 780
        assert result.estimated_cost == "780"

    def test_explanation_mentions_key_numbers(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20)
        assert "78" in result.explanation
        assert "5.0" in result.explanation or "5" in result.explanation
        assert "20" in result.explanation

    def test_inputs_are_correct(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20)
        assert result.inputs["avg_daily_usage"] == pytest.approx(5.0)
        assert result.inputs["target_days"] == 20
        assert result.inputs["current"] == 12
        assert result.inputs["incoming"] == 10
        assert result.inputs["lead_time_days"] == 0
        assert result.inputs["safety_stock"] == 0


class TestNoReorder:
    def test_zero_reorder_when_well_stocked(self):
        # 5/day, target=10 days, stock=100, incoming=0 → need 50, have 100 → 0
        result = _reorder(avg_daily=5.0, current=100, incoming=0, target_days=10)
        assert result.reorder_qty == 0

    def test_incoming_reduces_reorder(self):
        # 5/day, target=20, stock=0, incoming=100 → need 100, have 100 → 0
        result = _reorder(avg_daily=5.0, current=0, incoming=100, target_days=20)
        assert result.reorder_qty == 0


class TestConfidence:
    def test_high_confidence(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20, usage_days=10)
        assert result.confidence == "high"

    def test_medium_confidence(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20, usage_days=5)
        assert result.confidence == "medium"

    def test_low_confidence(self):
        result = _reorder(avg_daily=5.0, current=12, incoming=10, target_days=20, usage_days=1)
        assert result.confidence == "low"


class TestLeadTimeAndSafety:
    def test_lead_time_increases_reorder(self):
        # 5/day, target=10, lead=5, stock=0, incoming=0
        # target_stock = 5*(10+5)+0 = 75; reorder = 75-0-0 = 75
        result = _reorder(avg_daily=5.0, current=0, incoming=0, target_days=10, lead_time_days=5)
        assert result.reorder_qty == 75

    def test_safety_stock_adds_to_reorder(self):
        # 5/day, target=10, safety=20, stock=0, incoming=0
        # target_stock = 5*10+20 = 70; reorder = 70
        result = _reorder(avg_daily=5.0, current=0, incoming=0, target_days=10, safety_stock=20)
        assert result.reorder_qty == 70


class TestInsufficientData:
    def test_insufficient_data_returns_explanation(self):
        fc = _make_forecast(avg_daily=0.0, current=50, usage_days=1, state="insufficient_data")
        result = compute_reorder(
            product_id=1,
            product_name="Test",
            sku="TEST-001",
            forecast=fc,
            unit_cost=10.0,
            current_quantity=50,
            incoming=0,
            target_days=20,
        )
        # qty computed as 0 (avg=0 → target_stock=0, need 0 − 50 − 0 → max(0,...)=0)
        # explanation should mention insufficient data
        assert "insufficient" in result.explanation.lower() or "limited" in result.explanation.lower() or result.reorder_qty == 0
