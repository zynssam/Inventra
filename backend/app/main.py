"""
app/main.py — FastAPI application entry point.

- Registers CORS for http://localhost:5173
- Mounts all routers under /api/v1
- Registers error handlers
- GET /api/v1/health
- Creates tables on startup (dev/test convenience; prod uses Alembic)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.errors import register_error_handlers
from app.routers import (
    auth,
    audit,
    categories,
    dashboard,
    dev,
    forecasting,
    products,
    recommendations,
    reports,
    settings as settings_router,
    suppliers,
    transactions,
    users,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup (dev convenience; prod uses Alembic)."""
    try:
        create_tables()
    except Exception as exc:
        import logging
        logging.getLogger("app").warning("create_tables skipped: %s", exc)
    yield


app = FastAPI(
    title="StockSense API",
    description="Inventory management backend — track smarter, restock earlier.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# In DEBUG mode allow all origins so any local dev port works.
# In production the explicit whitelist in config is used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=not settings.DEBUG,  # credentials incompatible with "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
register_error_handlers(app)


# ---------------------------------------------------------------------------
# Health check (public)
# ---------------------------------------------------------------------------

@app.get("/api/v1/health", tags=["meta"])
def health():
    from sqlalchemy import text
    from app.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}


# ---------------------------------------------------------------------------
# Meta / enums
# ---------------------------------------------------------------------------

@app.get("/api/v1/meta/enums", tags=["meta"])
def meta_enums():
    """Returns all enum values so the frontend dropdowns stay in sync."""
    return {
        "transaction_types": ["stock_in", "stock_out", "adjustment", "reversal", "po_receipt", "stocktake"],
        "roles": ["admin", "store_manager", "viewer"],
        "po_statuses": ["draft", "ordered", "partially_received", "received", "cancelled"],
        "stocktake_statuses": ["open", "applied", "cancelled"],
        "sort_fields": ["name", "sku", "current_quantity", "unit_cost"],
        "forecast_states": ["ok", "warning", "critical", "out_of_stock", "insufficient_data", "no_recent_usage"],
    }


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(categories.router, prefix=PREFIX)
app.include_router(suppliers.router, prefix=PREFIX)
app.include_router(products.router, prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(forecasting.router, prefix=PREFIX)
app.include_router(recommendations.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(audit.router, prefix=PREFIX)
app.include_router(settings_router.router, prefix=PREFIX)
app.include_router(dev.router, prefix=PREFIX)
