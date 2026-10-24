"""
app/models.py — shim that re-exports Member A's models.

⚠️  When Member A delivers the real models.py, REPLACE the single import
    line below with the real implementation (or just delete this file if
    Member A places models directly here). Delete app/_temp/models_temp.py too.
"""
# ONE import line — swap this when Member A delivers
from app._temp.models_temp import (  # noqa: F401
    Base,
    User,
    UserRole,
    Category,
    Supplier,
    Product,
    StockTransaction,
    TxType,
    PurchaseOrder,
    PurchaseOrderItem,
    POStatus,
    Stocktake,
    StocktakeLine,
    StocktakeStatus,
    Setting,
    AuditLog,
)
