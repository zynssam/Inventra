"""app/routers/settings.py — GET/PUT /settings"""
from app.database import get_db
from app.dependencies import require_role
from app.models import User
from app.schemas import SettingsOut, SettingsUpdate
from app.services.audit_service import audit
from app.services.settings_service import apply_settings_update, get_settings
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def read_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "store_manager", "viewer")),
):
    s = get_settings(db)
    return SettingsOut(**s.__dict__)


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
    return SettingsOut(**result.__dict__)
