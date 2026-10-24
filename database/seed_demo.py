"""Demo seed (owner: Member A). Callable as seed_demo(db) and as CLI: python -m database.seed_demo
Every ledger row is written chronologically so balance_after and current_quantity are consistent.
Run from the repository root with DATABASE_URL set."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .models import (Category, Product, PurchaseOrder, PurchaseOrderItem, Setting,
                     StockTransaction, Supplier, User)

DEMO_PASSWORD_HASH = "REPLACE_WITH_BCRYPT_HASH_FROM_B"   # B provides hash_password()

def _reset(db):
    db.execute(text("TRUNCATE audit_logs, stocktake_lines, stocktakes, purchase_order_items, "
                    "purchase_orders, stock_transactions, products, suppliers, categories, "
                    "settings, users RESTART IDENTITY CASCADE"))

def _post(db, product, delta, kind, when, user_id, reason=None):
    product.current_quantity += delta
    assert product.current_quantity >= 0, f"negative stock for {product.sku}"
    db.add(StockTransaction(product_id=product.id, txn_type=kind, quantity_delta=delta,
                            balance_after=product.current_quantity, reason=reason,
                            created_by=user_id, created_at=when))
    db.flush()

# (sku, name, category, cost, reorder_point, opening_qty, opened_days_ago, 30 daily usages or None)
def _pattern(kind):
    if kind == "steady":  return [4] * 30
    if kind == "spike":   return [2] * 20 + [9] * 10
    if kind == "almost":  return [5] * 30
    if kind == "dead":    return [0] * 30
    if kind == "little":  return [0] * 29 + [1]
    if kind == "openpo":  return [6] * 30

STORIES = [
    ("WID-001", "Steel Bolts M8",       "Hardware",  "0.40", 30, 400, 31, "steady"),
    ("WID-002", "Safety Gloves",        "Safety",    "3.20", 40, 160, 31, "almost"),   # almost out
    ("WID-003", "Machine Oil 1L",       "Consumables","6.50", 25, 300, 31, "spike"),   # spiking
    ("WID-004", "Copper Washers",       "Hardware",  "0.15", 50, 600, 31, "openpo"),   # open PO
    ("WID-005", "Obsolete Gasket Kit",  "Hardware",  "12.00", 5,  40, 31, "dead"),     # dead stock
    ("WID-006", "New Sensor Module",    "Electronics","18.00", 5, 10,  3, "little"),   # too little data
]

def seed_demo(db: Session, today: datetime | None = None):
    today = today or datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    _reset(db)

    admin = User(email="admin@stocksense.dev", full_name="Demo Admin", role="admin", password_hash=DEMO_PASSWORD_HASH)
    store = User(email="store@stocksense.dev", full_name="Store Manager", role="store_manager", password_hash=DEMO_PASSWORD_HASH)
    viewer = User(email="viewer@stocksense.dev", full_name="Viewer", role="viewer", password_hash=DEMO_PASSWORD_HASH)
    db.add_all([admin, store, viewer]); db.flush()

    sup = Supplier(name="Acme Supplies", contact_email="orders@acme.test", lead_time_days=5)
    db.add(sup)
    cats = {n: Category(name=n) for n in {s[2] for s in STORIES}}
    db.add_all(cats.values()); db.flush()

    db.add_all([Setting(key="forecast_window_days", value="30"),
                Setting(key="safety_stock_days", value="3"),
                Setting(key="lead_time_default_days", value="5")])

    products = {}
    for sku, name, cat, cost, rop, opening, opened_ago, kind in STORIES:
        p = Product(sku=sku, name=name, category_id=cats[cat].id, supplier_id=sup.id,
                    unit_cost=Decimal(cost), reorder_point=rop, current_quantity=0)
        db.add(p); db.flush()
        products[sku] = p
        start = today - timedelta(days=opened_ago)
        _post(db, p, opening, "stock_in", start, admin.id, "Opening stock")
        usage = _pattern(kind)
        # usage list covers the last 30 days, oldest first
        for i, qty in enumerate(usage):
            if qty:
                day = today - timedelta(days=29 - i)
                if day > start:
                    _post(db, p, -min(qty, p.current_quantity), "stock_out", day, store.id, "Issued to production")

    # open PO for WID-004
    po = PurchaseOrder(po_number="PO-DEMO-001", supplier_id=sup.id, status="ordered",
                       expected_date=(today + timedelta(days=3)).date(), created_by=admin.id)
    po.items.append(PurchaseOrderItem(product_id=products["WID-004"].id, quantity_ordered=200,
                                      quantity_received=0, unit_cost=Decimal("0.15")))
    db.add(po)
    db.commit()

def main():
    import os
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as db:
        seed_demo(db)
    print("Demo data loaded.")

if __name__ == "__main__":
    main()
