"""
app/services/inventory_service.py — the ONLY code allowed to change current_quantity.

Implements apply_movement() exactly as specified in architecture.md §4:
  - Row lock on the product (FOR UPDATE)
  - No negative stock → 409 INSUFFICIENT_STOCK
  - Signed quantity_delta, balance_after
  - Audit log row in the same transaction
  - Append-only ledger

Public API:
  apply_movement(db, user, product_id, delta, tx_type, reason, **refs) -> StockTransaction
  adjust(db, user, product_id, new_quantity|delta, reason) -> StockTransaction
  reverse_transaction(db, user, tx_id, reason) -> StockTransaction
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Product, StockTransaction, TxType
from app.services.audit_service import audit

# Transaction types that count as "usage" for forecasting
USAGE_TYPES = {TxType.sale, TxType.issue, TxType.consumption}


def apply_movement(
    db: Session,
    user,
    product_id: int,
    delta: int,
    tx_type: TxType,
    reason: str,
    supplier_id: int | None = None,
    recipient: str | None = None,
    purchase_order_id: int | None = None,
    client_request_id: str | None = None,
    reference_id: int | None = None,
) -> StockTransaction:
    """
    Atomic stock movement: lock product row → validate → update qty →
    insert ledger row → insert audit log → return the new transaction.

    The caller must NOT wrap this in its own begin(); apply_movement manages
    the transaction boundary internally.
    """
    if delta == 0:
        raise ApiError(422, "VALIDATION_ERROR", "quantity_delta cannot be zero")

    # Idempotency check: if client_request_id already used, return existing tx
    if client_request_id is not None:
        existing = db.execute(
            select(StockTransaction).where(
                StockTransaction.client_request_id == client_request_id
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    with db.begin_nested():
        # Row-level lock to prevent race conditions.
        # architecture.md: SQLite does not support FOR UPDATE, skip it.
        stmt = select(Product).where(Product.id == product_id)
        try:
            dialect = db.get_bind().dialect.name
        except Exception:
            dialect = "unknown"
        if dialect != "sqlite":
            stmt = stmt.with_for_update()
        p = db.execute(stmt).scalar_one_or_none()

        if p is None:
            raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
        if p.is_archived:
            raise ApiError(409, "PRODUCT_ARCHIVED", f"Product '{p.name}' is archived")

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
            type=tx_type,
            quantity_delta=delta,
            balance_after=new_qty,
            user_id=user.id,
            supplier_id=supplier_id,
            recipient=recipient,
            reason=reason,
            reference_id=reference_id,
            purchase_order_id=purchase_order_id,
            client_request_id=client_request_id,
        )
        db.add(tx)
        db.flush()  # so tx.id is populated before audit

        audit(
            db,
            user,
            "STOCK_" + tx_type.value.upper(),
            "product",
            p.id,
            {"delta": delta, "balance_after": new_qty, "tx_id": tx.id},
        )

    db.refresh(tx)
    return tx


def adjust(
    db: Session,
    user,
    product_id: int,
    reason: str,
    new_quantity: int | None = None,
    delta: int | None = None,
) -> StockTransaction:
    """
    Admin-only adjustment: accepts either a new absolute quantity or a signed delta.
    """
    if new_quantity is None and delta is None:
        raise ApiError(422, "VALIDATION_ERROR", "Provide new_quantity or delta")

    if new_quantity is not None:
        # We need the current qty to compute the delta
        p = db.get(Product, product_id)
        if p is None:
            raise ApiError(404, "NOT_FOUND", f"Product {product_id} not found")
        effective_delta = new_quantity - p.current_quantity
    else:
        effective_delta = delta  # type: ignore[assignment]

    return apply_movement(
        db, user, product_id, effective_delta, TxType.adjustment, reason
    )


def reverse_transaction(
    db: Session,
    user,
    tx_id: int,
    reason: str,
) -> StockTransaction:
    """
    Create a reversal row that is the exact opposite of the original transaction.
    Raises ALREADY_REVERSED if another reversal already references this tx.
    Raises INSUFFICIENT_STOCK if reversing a stock-out would go below 0 (shouldn't
    happen for stock-in reversals, but protects stock-out reversals).
    """
    original = db.get(StockTransaction, tx_id)
    if original is None:
        raise ApiError(404, "NOT_FOUND", f"Transaction {tx_id} not found")

    # Check if already reversed
    existing_reversal = db.execute(
        select(StockTransaction).where(StockTransaction.reference_id == tx_id)
    ).scalar_one_or_none()
    if existing_reversal is not None:
        raise ApiError(409, "ALREADY_REVERSED", "This transaction has already been reversed")

    reversal_delta = -original.quantity_delta

    return apply_movement(
        db,
        user,
        original.product_id,
        reversal_delta,
        TxType.reversal,
        reason,
        reference_id=tx_id,
    )
