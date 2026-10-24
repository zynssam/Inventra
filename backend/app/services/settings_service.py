"""
app/services/settings_service.py — helper to read/write the key/value settings table.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Setting
from app.schemas import SETTING_DEFAULTS, SETTING_INT_KEYS, SettingsOut


def get_settings(db: Session) -> SettingsOut:
    rows = db.query(Setting).all()
    kv = {r.key: r.value for r in rows}
    # Fill in any missing keys with defaults
    merged = {**SETTING_DEFAULTS, **kv}
    return SettingsOut(
        default_target_days=int(merged["default_target_days"]),
        usage_window_days=int(merged["usage_window_days"]),
        min_usage_days=int(merged["min_usage_days"]),
        warning_days=int(merged["warning_days"]),
        critical_days=int(merged["critical_days"]),
        currency=merged["currency"],
        org_name=merged["org_name"],
    )


def upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))


def apply_settings_update(db: Session, updates: dict) -> SettingsOut:
    for key, val in updates.items():
        if val is not None:
            upsert_setting(db, key, str(val))
    db.commit()
    return get_settings(db)
