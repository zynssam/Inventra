"""
app/_temp/models_temp.py  — TEMPORARY stand-in for Member A's models.py

⚠️  DELETE THIS FILE and remove the shim in app/models.py once Member A
    delivers backend/app/models.py.

Follows architecture.md §5 exactly.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    admin = "admin"
    storekeeper = "storekeeper"
    viewer = "viewer"


class TxType(str, enum.Enum):
    purchase = "purchase"
    return_in = "return_in"
    sale = "sale"
    issue = "issue"
    consumption = "consumption"
    adjustment = "adjustment"
    reversal = "reversal"


class POStatus(str, enum.Enum):
    draft = "draft"
    ordered = "ordered"
    partially_received = "partially_received"
    received = "received"
    cancelled = "cancelled"


class StocktakeStatus(str, enum.Enum):
    in_progress = "in_progress"
    finalized = "finalized"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.viewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    transactions: Mapped[list["StockTransaction"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    products: Mapped[list["Product"]] = relationship(back_populates="default_supplier")
    transactions: Mapped[list["StockTransaction"]] = relationship(back_populates="supplier")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("current_quantity >= 0", name="ck_products_qty_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )
    default_supplier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True
    )
    unit: Mapped[str] = mapped_column(String(50), default="pcs", nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    selling_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    category: Mapped["Category | None"] = relationship(back_populates="products")
    default_supplier: Mapped["Supplier | None"] = relationship(back_populates="products")
    transactions: Mapped[list["StockTransaction"]] = relationship(back_populates="product")


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    type: Mapped[TxType] = mapped_column(Enum(TxType), nullable=False, index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True
    )
    recipient: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reference_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stock_transactions.id"), nullable=True
    )
    purchase_order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=True
    )
    client_request_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    product: Mapped["Product"] = relationship(back_populates="transactions")
    user: Mapped["User"] = relationship(back_populates="transactions")
    supplier: Mapped["Supplier | None"] = relationship(back_populates="transactions")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    status: Mapped[POStatus] = mapped_column(Enum(POStatus), default=POStatus.draft, nullable=False)
    order_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order")
    transactions: Mapped[list["StockTransaction"]] = relationship(
        primaryjoin="StockTransaction.purchase_order_id == PurchaseOrder.id",
        foreign_keys="StockTransaction.purchase_order_id",
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class Stocktake(Base):
    __tablename__ = "stocktakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[StocktakeStatus] = mapped_column(
        Enum(StocktakeStatus), default=StocktakeStatus.in_progress, nullable=False
    )
    started_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["StocktakeLine"]] = relationship(back_populates="stocktake")


class StocktakeLine(Base):
    __tablename__ = "stocktake_lines"
    __table_args__ = (UniqueConstraint("stocktake_id", "product_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stocktake_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocktakes.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    system_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    counted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    scanned_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    stocktake: Mapped["Stocktake"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")
