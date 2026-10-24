"""
app/queries/dashboard.py — wraps Member A's database/dashboard.py.
Member A's function names: summary(), movement_chart(), top_used(), category_value(), alerts_base()
"""
from __future__ import annotations

from sqlalchemy.orm import Session


def dashboard_summary(db: Session) -> dict:
    try:
        from database.dashboard import summary
        return summary(db)
    except Exception:
        return {}


def movement_chart(db: Session, days: int = 30) -> list[dict]:
    try:
        from database.dashboard import movement_chart as _mc
        return _mc(db, days)
    except Exception:
        return []


def top_used(db: Session, days: int = 30, limit: int = 5) -> list[dict]:
    try:
        from database.dashboard import top_used as _tu
        return _tu(db, days, limit)
    except Exception:
        return []


def category_value(db: Session) -> list[dict]:
    try:
        from database.dashboard import category_value as _cv
        return _cv(db)
    except Exception:
        return []


def alerts_base(db: Session) -> list[dict]:
    try:
        from database.dashboard import alerts_base as _ab
        return _ab(db)
    except Exception:
        return []
