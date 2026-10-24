"""
app/schemas.py — all Pydantic v2 request/response models.

Rules enforced here:
- password_hash is NEVER included in any response schema.
- Datetimes serialised as UTC ISO-8601 strings.
- Monetary values returned as str (Decimal serialisation).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Generic pagination wrapper
# ---------------------------------------------------------------------------

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Shared base config
# ---------------------------------------------------------------------------

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserOut(ORMBase):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(admin|storekeeper|viewer)$")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, pattern="^(admin|storekeeper|viewer)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryOut(ORMBase):
    id: int
    name: str
    description: Optional[str] = None
    product_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------

class SupplierOut(ORMBase):
    id: int
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_archived: bool
    created_at: datetime


class SupplierDetail(SupplierOut):
    product_count: int = 0
    total_purchased_value: str = "0.00"


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_person: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    contact_person: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = None


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class CategoryBrief(ORMBase):
    id: int
    name: str


class ProductOut(ORMBase):
    id: int
    name: str
    sku: str
    category: Optional[CategoryBrief] = None
    unit: str
    current_quantity: int
    minimum_stock: int
    unit_cost: str
    selling_price: Optional[str] = None
    lead_time_days: int
    safety_stock: int
    target_days: Optional[int] = None
    location: Optional[str] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    # computed fields added by the router
    status: Optional[str] = None
    forecast_state: Optional[str] = None
    days_until_stockout: Optional[float] = None

    @field_validator("unit_cost", "selling_price", mode="before")
    @classmethod
    def coerce_decimal_to_str(cls, v):
        if v is None:
            return None
        if isinstance(v, Decimal):
            return str(v)
        return str(v) if not isinstance(v, str) else v


class ProductDetail(ProductOut):
    default_supplier_id: Optional[int] = None
    forecast: Optional[dict] = None
    recommendation: Optional[dict] = None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    sku: str = Field(min_length=1, max_length=100)
    category_id: Optional[int] = None
    default_supplier_id: Optional[int] = None
    unit: str = Field(default="pcs", max_length=50)
    minimum_stock: int = Field(default=0, ge=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    lead_time_days: int = Field(default=0, ge=0)
    safety_stock: int = Field(default=0, ge=0)
    target_days: Optional[int] = Field(default=None, ge=1)
    location: Optional[str] = Field(default=None, max_length=200)
    initial_quantity: Optional[int] = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    category_id: Optional[int] = None
    default_supplier_id: Optional[int] = None
    unit: Optional[str] = Field(default=None, max_length=50)
    minimum_stock: Optional[int] = Field(default=None, ge=0)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    lead_time_days: Optional[int] = Field(default=None, ge=0)
    safety_stock: Optional[int] = Field(default=None, ge=0)
    target_days: Optional[int] = Field(default=None, ge=1)
    location: Optional[str] = Field(default=None, max_length=200)


# ---------------------------------------------------------------------------
# Stock Transactions
# ---------------------------------------------------------------------------

class TransactionOut(ORMBase):
    id: int
    product_id: int
    type: str
    quantity_delta: int
    balance_after: int
    user_id: int
    supplier_id: Optional[int] = None
    recipient: Optional[str] = None
    reason: str
    reference_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    client_request_id: Optional[str] = None
    created_at: datetime
    # Populated by the router on write endpoints
    product: Optional["ProductOut"] = None


class StockInRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    type: str = Field(pattern="^(purchase|return_in)$")
    supplier_id: Optional[int] = None
    reason: str = Field(min_length=1)
    purchase_order_id: Optional[int] = None
    client_request_id: Optional[str] = Field(default=None, max_length=100)


class StockOutRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    type: str = Field(pattern="^(sale|issue|consumption)$")
    recipient: Optional[str] = Field(default=None, max_length=300)
    reason: str = Field(min_length=1)
    client_request_id: Optional[str] = Field(default=None, max_length=100)


class AdjustmentRequest(BaseModel):
    product_id: int
    reason: str = Field(min_length=1)
    new_quantity: Optional[int] = Field(default=None, ge=0)
    delta: Optional[int] = None

    @model_validator(mode="after")
    def check_one_of(self) -> "AdjustmentRequest":
        if self.new_quantity is None and self.delta is None:
            raise ValueError("Provide either new_quantity or delta")
        if self.new_quantity is not None and self.delta is not None:
            raise ValueError("Provide only one of new_quantity or delta")
        return self


class ReverseRequest(BaseModel):
    reason: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------

class ForecastOut(BaseModel):
    product_id: int
    current_quantity: int
    avg_daily_usage: Optional[float] = None
    window_days: int
    usage_days_observed: int
    days_until_stockout: Optional[float] = None
    projected_stockout_date: Optional[date] = None
    state: str
    explanation: str
    trend: str = "steady"


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class RecommendationInputs(BaseModel):
    avg_daily_usage: float
    window_days: int
    target_days: int
    lead_time_days: int
    safety_stock: int
    current: int
    incoming: int


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
    window_days: Optional[int] = Field(default=None, gt=0)
    lead_time_days: Optional[int] = Field(default=None, ge=0)
    safety_days: Optional[int] = Field(default=None, ge=0)


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
    severity: str  # "critical" | "warning" | "low_stock" | "out_of_stock"
    alert_type: str
    message: str


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class StockMovementRow(BaseModel):
    id: int
    product_name: str
    sku: str
    type: str
    quantity_delta: int
    balance_after: int
    reason: str
    user_name: str
    created_at: datetime


class InventoryValuationRow(BaseModel):
    product_id: int
    product_name: str
    sku: str
    category: Optional[str]
    current_quantity: int
    unit_cost: str
    total_value: str


class StockStatusRow(BaseModel):
    product_id: int
    product_name: str
    sku: str
    status: str
    current_quantity: int
    minimum_stock: int
    unit_cost: str
    total_value: str


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SETTING_DEFAULTS: dict[str, str] = {
    "default_target_days": "20",
    "usage_window_days": "14",
    "min_usage_days": "3",
    "warning_days": "14",
    "critical_days": "7",
    "currency": "INR",
    "org_name": "StockSense",
}

SETTING_INT_KEYS = {
    "default_target_days", "usage_window_days", "min_usage_days",
    "warning_days", "critical_days",
}


class SettingsOut(BaseModel):
    default_target_days: int
    usage_window_days: int
    min_usage_days: int
    warning_days: int
    critical_days: int
    currency: str
    org_name: str


class SettingsUpdate(BaseModel):
    default_target_days: Optional[int] = Field(default=None, ge=1)
    usage_window_days: Optional[int] = Field(default=None, ge=1)
    min_usage_days: Optional[int] = Field(default=None, ge=1)
    warning_days: Optional[int] = Field(default=None, ge=1)
    critical_days: Optional[int] = Field(default=None, ge=1)
    currency: Optional[str] = Field(default=None, max_length=10)
    org_name: Optional[str] = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_thresholds(self) -> "SettingsUpdate":
        c = self.critical_days
        w = self.warning_days
        if c is not None and w is not None and c >= w:
            raise ValueError("critical_days must be less than warning_days")
        return self


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

class AuditLogOut(ORMBase):
    id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[dict] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Meta / enums
# ---------------------------------------------------------------------------

class MetaEnums(BaseModel):
    transaction_types: list[str]
    roles: list[str]
    po_statuses: list[str]
    stocktake_statuses: list[str]
    units: list[str]
    sort_fields: list[str]
