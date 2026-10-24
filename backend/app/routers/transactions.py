"""
app/routers/transactions.py — stock movements endpoints.

POST /transactions/stock-in
POST /transactions/stock-out
POST /transactions/adjustments  (admin)
POST /transactions/{id}/reverse  (admin)
GET  /transactions
GET  /transactions/{id}
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import ApiError
from app.models import Product, StockTransaction, TxType, User
from app.schemas import (
    AdjustmentRequest,
    Page,
    ProductOut,
    ReverseRequest,
    StockInRequest,
    StockOutRequest,
    TransactionOut,
)
from app.services.inventory_service import adjust, apply_movement, reverse_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))
AS = Depends(require_role("admin", "storekeeper"))
ADMIN = Depends(require_role("admin"))


def _tx_with_product(tx: StockTransaction, db: Session) -> TransactionOut:
    out = TransactionOut.model_validate(tx)
    p = db.get(Product, tx.product_id)
    if p:
        pout = ProductOut.model_validate(p)
        pout.unit_cost = str(p.unit_cost)
        pout.selling_price = str(p.selling_price) if p.selling_price is not None else None
        status = "out_of_stock" if p.current_quantity == 0 else \
                 "low_stock" if p.current_quantity <= p.minimum_stock else "healthy"
        pout.status = status
        out.product = pout
    return out


@router.post("/stock-in", response_model=TransactionOut, status_code=201)
def stock_in(
    body: StockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    tx = apply_movement(
        db,
        current_user,
        body.product_id,
        body.quantity,
        TxType(body.type),
        body.reason,
        supplier_id=body.supplier_id,
        purchase_order_id=body.purchase_order_id,
        client_request_id=body.client_request_id,
    )
    db.commit()
    db.refresh(tx)
    return _tx_with_product(tx, db)


@router.post("/stock-out", response_model=TransactionOut, status_code=201)
def stock_out(
    body: StockOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "storekeeper")),
):
    tx = apply_movement(
        db,
        current_user,
        body.product_id,
        -body.quantity,
        TxType(body.type),
        body.reason,
        recipient=body.recipient,
        client_request_id=body.client_request_id,
    )
    db.commit()
    db.refresh(tx)
    return _tx_with_product(tx, db)


@router.post("/adjustments", response_model=TransactionOut, status_code=201)
def make_adjustment(
    body: AdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    tx = adjust(
        db,
        current_user,
        body.product_id,
        body.reason,
        new_quantity=body.new_quantity,
        delta=body.delta,
    )
    db.commit()
    db.refresh(tx)
    return _tx_with_product(tx, db)


@router.post("/{tx_id}/reverse", response_model=TransactionOut, status_code=201)
def reverse(
    tx_id: int,
    body: ReverseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    tx = reverse_transaction(db, current_user, tx_id, body.reason)
    db.commit()
    db.refresh(tx)
    return _tx_with_product(tx, db)


@router.get("", response_model=Page[TransactionOut])
def list_transactions(
    product_id: Optional[int] = None,
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = ANY,
):
    query = db.query(StockTransaction)
    if product_id is not None:
        query = query.filter(StockTransaction.product_id == product_id)
    if type:
        query = query.filter(StockTransaction.type == type)
    if user_id is not None:
        query = query.filter(StockTransaction.user_id == user_id)
    if supplier_id is not None:
        query = query.filter(StockTransaction.supplier_id == supplier_id)
    if date_from:
        query = query.filter(StockTransaction.created_at >= date_from)
    if date_to:
        query = query.filter(StockTransaction.created_at <= date_to)
    if q:
        query = query.filter(
            or_(
                StockTransaction.reason.ilike(f"%{q}%"),
                StockTransaction.recipient.ilike(f"%{q}%"),
            )
        )
    total = query.count()
    items = query.order_by(StockTransaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, db: Session = Depends(get_db), _: User = ANY):
    tx = db.get(StockTransaction, tx_id)
    if tx is None:
        raise ApiError(404, "NOT_FOUND", f"Transaction {tx_id} not found")
    return _tx_with_product(tx, db)
