"""app/routers/transactions.py — stock movements via inventory_service"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import StockTransaction, User
from app.schemas import (
    AdjustmentRequest, Page, ReverseRequest,
    StockInRequest, StockOutRequest, TransactionOut,
)
from app.services.audit_service import audit
from app.services.inventory_service import apply_movement, reverse_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])

ANY = Depends(require_role("admin", "store_manager", "viewer"))
AS  = Depends(require_role("admin", "store_manager"))
ADMIN = Depends(require_role("admin"))


@router.get("", response_model=Page[TransactionOut])
def list_transactions(
    product_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    q = db.query(StockTransaction)
    if product_id:
        q = q.filter(StockTransaction.product_id == product_id)
    total = q.count()
    items = q.order_by(StockTransaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/stock-in", response_model=TransactionOut, status_code=201)
def stock_in(
    body: StockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    tx = apply_movement(
        db=db,
        product_id=body.product_id,
        delta=body.quantity,
        tx_type=body.type,
        user_id=current_user.id,
        reason=body.reason,
        client_request_id=body.client_request_id,
    )
    db.commit()
    return tx


@router.post("/stock-out", response_model=TransactionOut, status_code=201)
def stock_out(
    body: StockOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    tx = apply_movement(
        db=db,
        product_id=body.product_id,
        delta=-body.quantity,
        tx_type=body.type,
        user_id=current_user.id,
        reason=body.reason,
        client_request_id=body.client_request_id,
    )
    db.commit()
    return tx


@router.post("/adjustments", response_model=TransactionOut, status_code=201)
def adjustment(
    body: AdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    from app.models import Product
    p = db.get(Product, body.product_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"Product {body.product_id} not found")
    delta = body.new_quantity - p.current_quantity
    if delta == 0:
        raise ApiError(400, "VALIDATION_ERROR", "new_quantity equals current quantity — no change")
    tx = apply_movement(
        db=db,
        product_id=body.product_id,
        delta=delta,
        tx_type="adjustment",
        user_id=current_user.id,
        reason=body.reason or "Manual adjustment",
        client_request_id=body.client_request_id,
    )
    audit(db, current_user, "ADJUSTMENT", "product", body.product_id,
          {"from": p.current_quantity, "to": body.new_quantity})
    db.commit()
    return tx


@router.post("/{transaction_id}/reverse", response_model=TransactionOut, status_code=201)
def reverse(
    transaction_id: int,
    body: ReverseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "store_manager")),
):
    tx = reverse_transaction(
        db=db,
        original_id=transaction_id,
        user_id=current_user.id,
        reason=body.reason,
    )
    db.commit()
    return tx
