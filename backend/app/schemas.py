"""
app/schemas.py — All Pydantic v2 request/response models.

Aligned with Member A's real schema (database/models.py):
  - User.full_name (not .name)
  - User.role is plain str; roles: admin | store_manager | viewer
  - Product.is_active (not .is_archived; inverted!)
  - Product.reorder_point (not .minimum_stock)
  - Product.supplier_id (not .default_supplier_id)
  - StockTransaction.txn_type (not .type)
  - StockTransaction.created_by (not .user_id)
  - StockTransaction.reverses_id (not .reversal_of_id)
  - TXN_TYPES: stock_in | stock_out | adjustment | reversal | po_receipt | stocktake
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

T = TypeVar("T")

VALID_ROLES = {"admin", "store_manager", "viewer"}
VALID_TXN_TYPES = {"stock_in", "stock_out", "adjustment", "reversal", "po_receipt", "stocktake"}


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8)
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=120)
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        return v


class UserOut(ORMBase):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryOut(ORMBase):
    id: int
    name: str
    description: Optional[str] = None


class CategoryBrief(ORMBase):
    id: int
    name: str


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------

class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=40)
    lead_time_days: int = Field(default=7, ge=0)
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    lead_time_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class SupplierOut(ORMBase):
    id: int
    name: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    lead_time_days: int
    is_active: bool


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=50)
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    unit: str = "pcs"
    unit_cost: str = "0.00"
    initial_quantity: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=0, ge=0)
    min_order_qty: int = Field(default=1, ge=1)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    unit: Optional[str] = None
    unit_cost: Optional[str] = None
    reorder_point: Optional[int] = Field(None, ge=0)
    min_order_qty: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class ProductOut(ORMBase):
    id: int
    name: str
    sku: str
    category: Optional[CategoryBrief] = None
    unit: str
    current_quantity: int
    reorder_point: int
    unit_cost: str
    is_active: bool
    created_at: datetime
    # computed fields added by the router
    status: Optional[str] = None
    forecast_state: Optional[str] = None
    days_until_stockout: Optional[float] = None

    @field_validator("unit_cost", mode="before")
    @classmethod
    def coerce_decimal_to_str(cls, v):
        if v is None:
            return "0.00"
        return str(v) if not isinstance(v, str) else v


class ProductDetail(ProductOut):
    supplier_id: Optional[int] = None
    min_order_qty: int = 1


class SupplierBrief(ORMBase):
    id: int
    name: str


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class StockInRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    type: str = "stock_in"
    reason: Optional[str] = None
    client_request_id: Optional[str] = None

    @field_validator("type")
    @classmethod
    def valid_type(cls, v):
        if v not in {"stock_in", "po_receipt"}:
            raise ValueError("type must be stock_in or po_receipt")
        return v


class StockOutRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    type: str = "stock_out"
    reason: Optional[str] = None
    client_request_id: Optional[str] = None

    @field_validator("type")
    @classmethod
    def valid_type(cls, v):
        if v not in {"stock_out", "stocktake"}:
            raise ValueError("type must be stock_out or stocktake")
        return v


class AdjustmentRequest(BaseModel):
    product_id: int
    new_quantity: int = Field(ge=0)
    reason: Optional[str] = None
    client_request_id: Optional[str] = None


class ReverseRequest(BaseModel):
    reason: Optional[str] = None


class TransactionOut(ORMBase):
    id: int
    product_id: int
    txn_type: str
    quantity_delta: int
    balance_after: int
    reason: Optional[str] = None
    reverses_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

class ForecastOut(BaseModel):
    product_id: int
    current_quantity: int
    avg_daily_usage: Optional[float]
    window_days: int
    usage_days_observed: int
    days_until_stockout: Optional[float]
    projected_stockout_date: Optional[date]
    state: str   # ok | warning | critical | out_of_stock | insufficient_data | no_recent_usage
    explanation: str
    trend: Optional[str]   # rising | steady | falling


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class RecommendationInputs(BaseModel):
    avg_daily_usage: float
    target_days: int
    current: int
    incoming: int
    lead_time_days: int
    safety_stock: int


class RecommendationOut(BaseModel):
    product_id: int
    product_name: str
    sku: str
    reorder_qty: int
    estimated_cost: str
    explanation: str
    inputs: RecommendationInputs
    confidence: str
    forecast_state: str


class RecommendationListOut(BaseModel):
    items: list[RecommendationOut]
    total_estimated_cost: str


class SimulateRequest(BaseModel):
    target_days: int = Field(gt=0)
    window_days: Optional[int] = None
    lead_time_days: Optional[int] = None
    safety_days: Optional[int] = None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    total_products: int
    total_units: int
    low_stock_count: int
    out_of_stock_count: int
    total_inventory_value: str
    critical_forecast_count: int
    health_score: float


class AlertOut(BaseModel):
    product_id: int
    product_name: str
    sku: str
    current_quantity: int
    severity: str   # critical | warning
    alert_type: str  # out_of_stock | low_stock | forecast
    message: str


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditLogOut(ORMBase):
    id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[Any] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsOut(BaseModel):
    usage_window_days: int
    warning_days: int
    critical_days: int
    min_usage_days: int
    default_target_days: int


class SettingsUpdate(BaseModel):
    usage_window_days: Optional[int] = Field(None, gt=0)
    warning_days: Optional[int] = Field(None, gt=0)
    critical_days: Optional[int] = Field(None, gt=0)
    min_usage_days: Optional[int] = Field(None, ge=1)
    default_target_days: Optional[int] = Field(None, gt=0)
