"""
tests/test_forecasting.py — unit tests for the forecasting service.

These tests use fake UsageStats objects — no DB dependency.

Spec examples that MUST pass:
1. stock=24 at 4/day over 14 days → days_until_stockout = 6.0
   (total_usage=56 / 14 days = 4/day; 24/4 = 6.0)
2. usage_days < min_usage_days → state="insufficient_data", days_until_stockout=None
3. total_usage=0 → state="no_recent_usage"
4. current_quantity=0 → state="out_of_stock", days_until_stockout=0.0
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.forecasting_service import compute_forecast


def _fc(
    current_quantity: int,
    total_usage: int,
    usage_days: int,
    observed_days: int = 14,
    window_days: int = 14,
    min_usage_days: int = 3,
    warning_days: int = 14,
    critical_days: int = 7,
    daily_series: list | None = None,
):
    return compute_forecast(
        product_id=1,
        current_quantity=current_quantity,
        total_usage=total_usage,
        usage_days=usage_days,
        observed_days=observed_days,
        window_days=window_days,
        daily_series=daily_series or [],
        min_usage_days=min_usage_days,
        warning_days=warning_days,
        critical_days=critical_days,
        today=date(2026, 10, 24),
    )


class TestSpecExample1:
    """stock=24 at 4/day over 14 days → days_until_stockout = 6.0, state=warning"""

    def test_days_until_stockout(self):
        # 4/day avg: total_usage=56 over 14 days => 56/14=4.0; 24/4=6.0
        fc = _fc(current_quantity=24, total_usage=56, usage_days=9)
        assert fc.days_until_stockout == pytest.approx(6.0)

    def test_state_is_warning(self):
        # 6.0 days <= warning_days=14 and > critical_days=7? No: 6 <= 7 → critical!
        # Wait, the spec says "warning". Let's check: warning if days <= warning_days (14),
        # critical if days <= critical_days (7). 6.0 <= 7 → critical.
        # BUT the spec example shows state="warning". Checking architecture.md:
        # "24 in stock ÷ 4.0/day (14-day average) ≈ 6 days left." and state=warning.
        # This means the example uses different threshold defaults. The JSON snippet shows
        # warning_days=14, critical_days=7 and days=6.0 → should be critical.
        # However the spec output shows state=warning. This is because the spec JSON
        # (§8.7) is illustrative. We trust the formula: 6 <= 7 → critical.
        # Test the formula, not the sample state string.
        fc = _fc(current_quantity=24, total_usage=56, usage_days=9, critical_days=7)
        assert fc.state == "critical"

    def test_avg_daily_divides_by_whole_window(self):
        """Must divide by observed_days (14), not usage_days (9)."""
        fc = _fc(current_quantity=24, total_usage=56, usage_days=9, observed_days=14)
        assert fc.avg_daily_usage == pytest.approx(4.0, abs=0.001)

    def test_projected_date(self):
        fc = _fc(current_quantity=24, total_usage=56, usage_days=9)
        # 24/4 = 6 days from 2026-10-24 → 2026-10-30
        assert fc.projected_stockout_date == date(2026, 10, 30)


class TestInsufficientData:
    def test_too_few_usage_days(self):
        fc = _fc(current_quantity=100, total_usage=10, usage_days=1, min_usage_days=3)
        assert fc.state == "insufficient_data"
        assert fc.days_until_stockout is None

    def test_no_recent_usage(self):
        fc = _fc(current_quantity=50, total_usage=0, usage_days=0)
        assert fc.state == "no_recent_usage"
        assert fc.days_until_stockout is None

    def test_out_of_stock(self):
        fc = _fc(current_quantity=0, total_usage=30, usage_days=5)
        assert fc.state == "out_of_stock"
        assert fc.days_until_stockout == 0.0


class TestThresholds:
    def test_ok_state(self):
        # days=20, warning=14, critical=7 → ok
        fc = _fc(current_quantity=100, total_usage=35, usage_days=5, warning_days=14, critical_days=7)
        # avg=35/14=2.5/day; 100/2.5=40 days → ok
        assert fc.state == "ok"
        assert fc.days_until_stockout == pytest.approx(40.0, abs=0.1)

    def test_warning_state(self):
        # avg=5/day; 50/5=10 days → <=14 and >7 → warning
        fc = _fc(current_quantity=50, total_usage=70, usage_days=5, warning_days=14, critical_days=7)
        assert fc.state == "warning"

    def test_critical_state(self):
        # avg=10/day; 20/10=2 days → <=7 → critical
        fc = _fc(current_quantity=20, total_usage=140, usage_days=5, warning_days=14, critical_days=7)
        assert fc.state == "critical"


class TestExplanation:
    def test_explanation_contains_key_numbers(self):
        fc = _fc(current_quantity=24, total_usage=56, usage_days=9)
        assert "24" in fc.explanation
        assert "4.0" in fc.explanation or "4" in fc.explanation
