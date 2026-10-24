"""StockSense schema (owner: Member A). SQLAlchemy 2.0 style."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


TXN_TYPES = ("stock_in", "stock_out", "adjustment", "reversal", "po_receipt", "stocktake")
PO_STATUSES = ("draft", "ordered", "partially_received", "received", "cancelled")
ROLES = ("admin", "store_manager", "viewer")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint(f"role IN {ROLES}", name="ck_users_role"),)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"))
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    current_quantity: Mapped[int] = mapped_column(Integer, default=0)   # cached ledger sum
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category: Mapped["Category"] = relationship()
    supplier: Mapped["Supplier"] = relationship()
    __table_args__ = (
        CheckConstraint("current_quantity >= 0", name="ck_products_qty_nonneg"),
        CheckConstraint("unit_cost >= 0", name="ck_products_cost_nonneg"),
    )


class StockTransaction(Base):
    """Append-only ledger. A DB trigger rejects UPDATE/DELETE."""
    __tablename__ = "stock_transactions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    txn_type: Mapped[str] = mapped_column(String(20))
    quantity_delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(255))
    reference_type: Mapped[str | None] = mapped_column(String(30))   # 'purchase_order', 'stocktake'
    reference_id: Mapped[int | None] = mapped_column(Integer)
    reverses_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_transactions.id", ondelete="RESTRICT"), unique=True)
    client_request_id: Mapped[str | None] = mapped_column(String(64), unique=True)  # idempotency
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("quantity_delta <> 0", name="ck_txn_delta_nonzero"),
        CheckConstraint("balance_after >= 0", name="ck_txn_balance_nonneg"),
        CheckConstraint(f"txn_type IN {TXN_TYPES}", name="ck_txn_type"),
        Index("ix_txn_product_created", "product_id", "created_at"),
        Index("ix_txn_created", "created_at"),
    )


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(String(30), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    expected_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan")
    __table_args__ = (CheckConstraint(f"status IN {PO_STATUSES}", name="ck_po_status"),)


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    quantity_ordered: Mapped[int] = mapped_column(Integer)
    quantity_received: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    __table_args__ = (
        CheckConstraint("quantity_ordered > 0", name="ck_poi_ordered_pos"),
        CheckConstraint("quantity_received >= 0 AND quantity_received <= quantity_ordered",
                        name="ck_poi_received_range"),
        UniqueConstraint("purchase_order_id", "product_id", name="uq_poi_order_product"),
        Index("ix_poi_product", "product_id"),
    )


class Stocktake(Base):
    __tablename__ = "stocktakes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="open")   # open | applied | cancelled
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lines: Mapped[list["StocktakeLine"]] = relationship(back_populates="stocktake", cascade="all, delete-orphan")


class StocktakeLine(Base):
    __tablename__ = "stocktake_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    stocktake_id: Mapped[int] = mapped_column(ForeignKey("stocktakes.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    system_quantity: Mapped[int] = mapped_column(Integer)
    counted_quantity: Mapped[int | None] = mapped_column(Integer)
    stocktake: Mapped["Stocktake"] = relationship(back_populates="lines")
    __table_args__ = (UniqueConstraint("stocktake_id", "product_id", name="uq_stl_take_product"),)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
