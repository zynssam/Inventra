"""
app/routers/reports.py — /reports/* endpoints

All support ?format=json (default) or ?format=csv.
CSV: UTF-8 BOM, formula-injection escaped.
Only builds the three reports in Member B's lane:
  stock-movements, inventory-valuation, stock-status
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Category, Product, StockTransaction, User
from app.services.reporting_service import build_csv, csv_filename

router = APIRouter(prefix="/reports", tags=["reports"])

ANY = Depends(require_role("admin", "storekeeper", "viewer"))


@router.get("/stock-movements")
def stock_movements_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    product_id: Optional[int] = None,
    category_id: Optional[int] = None,
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    format: str = "json",
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
    if date_from:
        query = query.filter(StockTransaction.created_at >= date_from)
    if date_to:
        query = query.filter(StockTransaction.created_at <= date_to)
    if category_id is not None:
        pids = [p.id for p in db.query(Product).filter(Product.category_id == category_id).all()]
        query = query.filter(StockTransaction.product_id.in_(pids))

    txs = query.order_by(StockTransaction.created_at.desc()).all()

    rows = []
    for tx in txs:
        p = db.get(Product, tx.product_id)
        u = db.get(User, tx.user_id)
        rows.append({
            "id": tx.id,
            "product_name": p.name if p else "",
            "sku": p.sku if p else "",
            "type": tx.type.value,
            "quantity_delta": tx.quantity_delta,
            "balance_after": tx.balance_after,
            "reason": tx.reason,
            "user_name": u.name if u else "",
            "created_at": tx.created_at.isoformat(),
        })

    if format == "csv":
        headers = ["ID", "Product", "SKU", "Type", "Delta", "Balance After", "Reason", "User", "Date"]
        csv_rows = [
            [r["id"], r["product_name"], r["sku"], r["type"], r["quantity_delta"],
             r["balance_after"], r["reason"], r["user_name"], r["created_at"]]
            for r in rows
        ]
        content = build_csv(headers, csv_rows)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{csv_filename("stock-movements")}"'},
        )
    return rows


@router.get("/inventory-valuation")
def inventory_valuation_report(
    format: str = "json",
    db: Session = Depends(get_db),
    _: User = ANY,
):
    products = db.query(Product).filter(Product.is_archived == False).all()  # noqa: E712
    categories = {c.id: c.name for c in db.query(Category).all()}

    # Group by category
    by_category: dict[str | None, list] = {}
    for p in products:
        cat_name = categories.get(p.category_id) if p.category_id else "Uncategorized"
        if cat_name not in by_category:
            by_category[cat_name] = []
        by_category[cat_name].append({
            "product_id": p.id,
            "product_name": p.name,
            "sku": p.sku,
            "category": cat_name,
            "current_quantity": p.current_quantity,
            "unit_cost": str(p.unit_cost),
            "total_value": str(round(float(p.unit_cost) * p.current_quantity, 2)),
        })

    subtotals = []
    grand_total = 0.0
    items = []
    for cat_name, cat_products in sorted(by_category.items(), key=lambda x: x[0] or ""):
        cat_total = sum(float(cp["total_value"]) for cp in cat_products)
        grand_total += cat_total
        items.extend(cat_products)
        subtotals.append({"category": cat_name, "total_value": str(round(cat_total, 2))})

    data = {"items": items, "subtotals": subtotals, "grand_total": str(round(grand_total, 2))}

    if format == "csv":
        headers = ["Product", "SKU", "Category", "Qty", "Unit Cost", "Total Value"]
        csv_rows = [[r["product_name"], r["sku"], r["category"], r["current_quantity"], r["unit_cost"], r["total_value"]] for r in items]
        content = build_csv(headers, csv_rows)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{csv_filename("inventory-valuation")}"'},
        )
    return data


@router.get("/stock-status")
def stock_status_report(
    format: str = "json",
    db: Session = Depends(get_db),
    _: User = ANY,
):
    products = db.query(Product).filter(Product.is_archived == False).all()  # noqa: E712
    rows = []
    for p in products:
        status = "out_of_stock" if p.current_quantity == 0 else \
                 "low_stock" if p.current_quantity <= p.minimum_stock else "healthy"
        rows.append({
            "product_id": p.id,
            "product_name": p.name,
            "sku": p.sku,
            "status": status,
            "current_quantity": p.current_quantity,
            "minimum_stock": p.minimum_stock,
            "unit_cost": str(p.unit_cost),
            "total_value": str(round(float(p.unit_cost) * p.current_quantity, 2)),
        })

    if format == "csv":
        headers = ["Product", "SKU", "Status", "Qty", "Min Stock", "Unit Cost", "Total Value"]
        csv_rows = [[r["product_name"], r["sku"], r["status"], r["current_quantity"],
                     r["minimum_stock"], r["unit_cost"], r["total_value"]] for r in rows]
        content = build_csv(headers, csv_rows)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{csv_filename("stock-status")}"'},
        )
    return rows
