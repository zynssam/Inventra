"""CRUD operations for products, categories, and suppliers.

Functions accept a SQLAlchemy Session and flush changes without committing.
The caller owns the transaction and should commit or roll it back.
"""
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Category, Product, PurchaseOrder, Supplier


def _update_fields(entity: Any, changes: Mapping[str, Any], allowed: set[str]) -> Any:
    unsupported = set(changes) - allowed
    if unsupported:
        names = ", ".join(sorted(unsupported))
        raise ValueError(f"Unsupported fields: {names}")
    for name, value in changes.items():
        setattr(entity, name, value)
    return entity


def create_category(db: Session, *, name: str, description: str | None = None) -> Category:
    category = Category(name=name, description=description)
    db.add(category)
    db.flush()
    return category


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


def update_category(db: Session, category_id: int, **changes: Any) -> Category | None:
    category = db.get(Category, category_id)
    if category is None:
        return None
    _update_fields(category, changes, {"name", "description"})
    db.flush()
    return category


def delete_category(db: Session, category_id: int) -> bool:
    category = db.get(Category, category_id)
    if category is None:
        return False
    product_count = db.scalar(
        select(func.count()).select_from(Product).where(Product.category_id == category_id)
    )
    if product_count:
        raise ValueError("Cannot delete a category while products use it.")
    db.delete(category)
    db.flush()
    return True


def create_supplier(
    db: Session,
    *,
    name: str,
    contact_email: str | None = None,
    phone: str | None = None,
    lead_time_days: int = 7,
    is_active: bool = True,
) -> Supplier:
    supplier = Supplier(
        name=name,
        contact_email=contact_email,
        phone=phone,
        lead_time_days=lead_time_days,
        is_active=is_active,
    )
    db.add(supplier)
    db.flush()
    return supplier


def get_supplier(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def list_suppliers(db: Session, *, include_inactive: bool = True) -> list[Supplier]:
    statement = select(Supplier)
    if not include_inactive:
        statement = statement.where(Supplier.is_active.is_(True))
    return list(db.scalars(statement.order_by(Supplier.name)))


def update_supplier(db: Session, supplier_id: int, **changes: Any) -> Supplier | None:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        return None
    _update_fields(
        supplier,
        changes,
        {"name", "contact_email", "phone", "lead_time_days", "is_active"},
    )
    db.flush()
    return supplier


def delete_supplier(db: Session, supplier_id: int) -> bool:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        return False
    order_count = db.scalar(
        select(func.count()).select_from(PurchaseOrder).where(
            PurchaseOrder.supplier_id == supplier_id
        )
    )
    if order_count:
        raise ValueError("Cannot delete a supplier while purchase orders reference it.")
    db.delete(supplier)
    db.flush()
    return True


def create_product(
    db: Session,
    *,
    sku: str,
    name: str,
    category_id: int | None = None,
    supplier_id: int | None = None,
    unit: str = "pcs",
    unit_cost: Decimal = Decimal("0"),
    reorder_point: int = 0,
    min_order_qty: int = 1,
) -> Product:
    """Create a product at zero stock; use the stock-movement workflow to add stock."""
    product = Product(
        sku=sku,
        name=name,
        category_id=category_id,
        supplier_id=supplier_id,
        unit=unit,
        unit_cost=unit_cost,
        current_quantity=0,
        reorder_point=reorder_point,
        min_order_qty=min_order_qty,
    )
    db.add(product)
    db.flush()
    return product


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def list_products(db: Session, *, include_inactive: bool = False) -> list[Product]:
    statement = select(Product)
    if not include_inactive:
        statement = statement.where(Product.is_active.is_(True))
    return list(db.scalars(statement.order_by(Product.name)))


def update_product(db: Session, product_id: int, **changes: Any) -> Product | None:
    """Update product details; stock quantity is maintained only by ledger operations."""
    product = db.get(Product, product_id)
    if product is None:
        return None
    _update_fields(
        product,
        changes,
        {
            "sku",
            "name",
            "category_id",
            "supplier_id",
            "unit",
            "unit_cost",
            "reorder_point",
            "min_order_qty",
            "is_active",
        },
    )
    db.flush()
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Soft-delete a product so existing transactions and reports remain intact."""
    product = db.get(Product, product_id)
    if product is None:
        return False
    product.is_active = False
    db.flush()
    return True
