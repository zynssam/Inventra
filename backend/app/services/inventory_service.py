"""
app/services/inventory_service.py

The ONLY place in the backend that mutates product.current_quantity.
Uses Member A's real column names:
  - StockTransaction.txn_type  (not .type)
  - StockTransaction.created_by (not .user_id)
  - StockTransaction.reverses_id (not .reversal_of_id)
  - Product.is_active (not .is_archived — and inverted: True means active)
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Product, StockTransaction
from app.services.audit_service import audit


def apply_movement(
    db: Session,
    *,
    product_id: int,
    delta: int,
    tx_type: str,
    user_id: int | None = None,
    reason: str | None = None,
    client_request_id: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    reverses_id: int | None = None,
) -> StockTransaction:
    """
    Apply a stock movement atomically.
    delta > 0 = stock in, delta < 0 = stock out.
    Raises ApiError on: product not found, product inactive, insufficient stock,
    duplicate client_request_id.
    """
    if delta == 0:
        raise ApiError(422, "VALIDATION_ERROR", "quantity_delta cannot be zero")

    # Idempotency check
    if client_request_id is not None:
        existing = db.execute(
            select(StockTransaction).where(
                StockTransaction.client_request_id == client_request_id
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    with db.begin_nested():
        # Row-level lock (skip on SQLite — not supported)
        stmt = select(Product).where(Product.id == product_id)
        try:
            if db.get_bind().dialect.name != "sqlite":
                stmt = stmt.with_for_update()
        except Exception:
            pass
        p = db.execute(stmt).scalar_one_or_none()

        if p is None:
            raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
        if not p.is_active:
            raise ApiError(409, "PRODUCT_INACTIVE", f"Product '{p.name}' is inactive")

        new_qty = p.current_quantity + delta
        if new_qty < 0:
            raise ApiError(
                409,
                "INSUFFICIENT_STOCK",
                f"Only {p.current_quantity} {p.unit} available",
                field="quantity",
            )

        p.current_quantity = new_qty

        tx = StockTransaction(
            product_id=p.id,
            txn_type=tx_type,
            quantity_delta=delta,
            balance_after=new_qty,
            reason=reason,
            created_by=user_id,
            client_request_id=client_request_id,
            reference_type=reference_type,
            reference_id=reference_id,
            reverses_id=reverses_id,
        )
        db.add(tx)
        db.flush()

    if user_id:
        user = db.get(type("User", (), {})._meta if False else __import__("app.models", fromlist=["User"]).User, user_id)
        audit(db, user, "STOCK_MOVEMENT", "product", product_id, {
            "txn_type": tx_type, "delta": delta, "balance_after": new_qty,
        })

    return tx


def reverse_transaction(
    db: Session,
    *,
    original_id: int,
    user_id: int | None = None,
    reason: str | None = None,
) -> StockTransaction:
    """Reverse a prior transaction. Fails if already reversed."""
    original = db.get(StockTransaction, original_id)
    if original is None:
        raise ApiError(404, "NOT_FOUND", f"Transaction {original_id} not found")

    # Check if already reversed
    already = db.execute(
        select(StockTransaction).where(StockTransaction.reverses_id == original_id)
    ).scalar_one_or_none()
    if already is not None:
        raise ApiError(409, "ALREADY_REVERSED", f"Transaction {original_id} has already been reversed")

    return apply_movement(
        db=db,
        product_id=original.product_id,
        delta=-original.quantity_delta,
        tx_type="reversal",
        user_id=user_id,
        reason=reason or f"Reversal of transaction {original_id}",
        reference_type="reversal",
        reference_id=original_id,
        reverses_id=original_id,
    )
