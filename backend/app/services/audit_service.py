"""
app/services/audit_service.py — write audit log rows.

Called from every mutation endpoint so that each create/update/stock action
produces exactly one log row with user, timestamp and before/after details.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(
    db: Session,
    user,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Append an audit log row.  Must be called *inside* the same DB transaction
    as the change being logged so they commit (or roll back) together.
    """
    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )
    db.add(log)
    return log
