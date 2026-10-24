"""
app/routers/dev.py — /dev/seed-demo and /dev/reset (admin, DEBUG=true only)

POST /dev/seed-demo: calls seed_demo(db) from app.seed (Member A's).
  If it doesn't exist, returns 501.
POST /dev/reset: clears all data.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import User

router = APIRouter(prefix="/dev", tags=["dev"])

ADMIN = Depends(require_role("admin"))


def _check_debug():
    if not settings.DEBUG:
        raise ApiError(403, "FORBIDDEN", "This endpoint is only available when DEBUG=true")


@router.post("/seed-demo")
def seed_demo(db: Session = Depends(get_db), _: User = ADMIN):
    _check_debug()
    try:
        from app.seed import seed_demo as _seed_demo  # Member A's file
        _seed_demo(db)
        return {"detail": "Demo data seeded successfully"}
    except ImportError:
        raise ApiError(501, "NOT_IMPLEMENTED", "Seed not available yet")


@router.post("/reset")
def reset_db(db: Session = Depends(get_db), _: User = ADMIN):
    _check_debug()
    from app.models import (
        AuditLog, PurchaseOrder, PurchaseOrderItem, StockTransaction,
        Stocktake, StocktakeLine, Product, Supplier, Category,
    )
    for model in [AuditLog, StocktakeLine, Stocktake, PurchaseOrderItem,
                  PurchaseOrder, StockTransaction]:
        db.query(model).delete()
    db.query(Product).delete()
    db.query(Supplier).delete()
    db.query(Category).delete()
    db.query(User).filter(User.role != "admin").delete()
    db.commit()
    return {"detail": "Database reset successfully"}
