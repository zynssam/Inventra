"""
app/services/settings_service.py

Reads/writes settings from the `settings` table (key/value store).
Provides a typed SettingsView so callers never deal with raw strings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import Setting

# ---------------------------------------------------------------------------
# Defaults and type registry
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "usage_window_days": 30,
    "warning_days": 14,
    "critical_days": 7,
    "min_usage_days": 3,
    "default_target_days": 30,
}

INT_KEYS = set(DEFAULTS.keys())


@dataclass
class SettingsView:
    usage_window_days: int
    warning_days: int
    critical_days: int
    min_usage_days: int
    default_target_days: int


def get_settings(db: Session) -> SettingsView:
    rows = db.query(Setting).all()
    kv = {r.key: r.value for r in rows}
    return SettingsView(
        usage_window_days=int(kv.get("usage_window_days", DEFAULTS["usage_window_days"])),
        warning_days=int(kv.get("warning_days", DEFAULTS["warning_days"])),
        critical_days=int(kv.get("critical_days", DEFAULTS["critical_days"])),
        min_usage_days=int(kv.get("min_usage_days", DEFAULTS["min_usage_days"])),
        default_target_days=int(kv.get("default_target_days", DEFAULTS["default_target_days"])),
    )


def apply_settings_update(db: Session, updates: dict[str, Any]) -> SettingsView:
    for key, value in updates.items():
        if key not in DEFAULTS:
            continue
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
    db.flush()
    return get_settings(db)
