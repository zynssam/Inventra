"""
app/routers/audit.py — GET /audit-logs (admin only)
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import AuditLog, User
from app.schemas import AuditLogOut, Page

router = APIRouter(prefix="/audit-logs", tags=["audit"])

ADMIN = Depends(require_role("admin"))


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = ADMIN,
):
    q = db.query(AuditLog)
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page(
        items=[AuditLogOut.model_validate(a) for a in items],
        total=total, page=page, page_size=page_size,
    )
