"""
app/routers/settings.py — GET /settings (any logged-in), PUT /settings (admin)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import User
from app.schemas import SettingsOut, SettingsUpdate
from app.services.audit_service import audit
from app.services.settings_service import apply_settings_update, get_settings

router = APIRouter(prefix="/settings", tags=["settings"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))
ADMIN = Depends(require_role("admin"))


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db), _: User = ANY):
    return get_settings(db)


@router.put("", response_model=SettingsOut)
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    updates = body.model_dump(exclude_unset=True)
    result = apply_settings_update(db, updates)
    audit(db, current_user, "SETTINGS_UPDATE", "settings", None, updates)
    db.commit()
    return result
