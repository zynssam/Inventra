"""app/routers/reports.py — /reports/* with JSON or CSV output"""

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
ANY = Depends(require_role("admin", "store_manager", "viewer"))


@router.get("/stock-movements")
def stock_movements_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    product_id: Optional[int] = None,
    category_id: Optional[int] = None,
    txn_type: Optional[str] = None,
    format: str = "json",
    db: Session = Depends(get_db),
    _: User = ANY,
):
    q = db.query(StockTransaction)
    if product_id:
        q = q.filter(StockTransaction.product_id == product_id)
    if txn_type:
        q = q.filter(StockTransaction.txn_type == txn_type)
    if date_from:
        q = q.filter(StockTransaction.created_at >= date_from)
    if date_to:
        q = q.filter(StockTransaction.created_at <= date_to)
    if category_id:
        pids = [p.id for p in db.query(Product).filter(Product.category_id == category_id).all()]
        q = q.filter(StockTransaction.product_id.in_(pids))

    txs = q.order_by(StockTransaction.created_at.desc()).all()
    rows = []
    for tx in txs:
        p = db.get(Product, tx.product_id)
        rows.append({
            "id": tx.id, "product_name": p.name if p else "", "sku": p.sku if p else "",
            "txn_type": tx.txn_type, "quantity_delta": tx.quantity_delta,
            "balance_after": tx.balance_after, "reason": tx.reason,
            "created_at": tx.created_at.isoformat(),
        })

    if format == "csv":
        headers = ["ID", "Product", "SKU", "Type", "Delta", "Balance After", "Reason", "Date"]
        csv_rows = [[r["id"], r["product_name"], r["sku"], r["txn_type"],
                     r["quantity_delta"], r["balance_after"], r["reason"], r["created_at"]] for r in rows]
        return Response(build_csv(headers, csv_rows), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{csv_filename("stock-movements")}"'})
    return rows


@router.get("/inventory-valuation")
def inventory_valuation_report(format: str = "json", db: Session = Depends(get_db), _: User = ANY):
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa
    categories = {c.id: c.name for c in db.query(Category).all()}
    rows = [
        {
            "product_name": p.name, "sku": p.sku,
            "category": categories.get(p.category_id, "Uncategorised"),
            "current_quantity": p.current_quantity,
            "unit_cost": str(p.unit_cost),
            "total_value": str(round(float(p.unit_cost) * p.current_quantity, 2)),
        }
        for p in products
    ]
    grand_total = str(round(sum(float(r["total_value"]) for r in rows), 2))
    data = {"items": rows, "grand_total": grand_total}

    if format == "csv":
        headers = ["Product", "SKU", "Category", "Qty", "Unit Cost", "Total Value"]
        csv_rows = [[r["product_name"], r["sku"], r["category"], r["current_quantity"],
                     r["unit_cost"], r["total_value"]] for r in rows]
        return Response(build_csv(headers, csv_rows), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{csv_filename("inventory-valuation")}"'})
    return data


@router.get("/stock-status")
def stock_status_report(format: str = "json", db: Session = Depends(get_db), _: User = ANY):
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa
    rows = [
        {
            "product_name": p.name, "sku": p.sku,
            "status": "out_of_stock" if p.current_quantity == 0
                      else "low_stock" if p.current_quantity <= p.reorder_point else "healthy",
            "current_quantity": p.current_quantity,
            "reorder_point": p.reorder_point,
        }
        for p in products
    ]
    if format == "csv":
        headers = ["Product", "SKU", "Status", "Qty", "Reorder Point"]
        csv_rows = [[r["product_name"], r["sku"], r["status"],
                     r["current_quantity"], r["reorder_point"]] for r in rows]
        return Response(build_csv(headers, csv_rows), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{csv_filename("stock-status")}"'})
    return rows
