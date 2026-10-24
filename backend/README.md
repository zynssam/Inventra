# StockSense — Backend API

FastAPI backend for the StockSense inventory management system.

---

## Prerequisites

- Python 3.11+ (3.14 works; 3.11–3.12 recommended for broadest wheel support)
- PostgreSQL 16 (for production) — Member A handles docker-compose
- SQLite (used automatically for local dev/tests)

---

## Quick Start

```bash
# 1. Create and activate venv
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env and configure
cp .env.example .env
# Edit .env: set DATABASE_URL and SECRET_KEY

# 4. Run the dev server (SQLite auto-created on first start)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs  
Health check: http://localhost:8000/api/v1/health

---

## Demo Logins

> Seed via `POST /api/v1/dev/seed-demo` (requires `DEBUG=true` in `.env`  
> and Member A's `app/seed.py` to be present).

| Role        | Email                    | Password   |
|-------------|--------------------------|------------|
| Admin       | admin@stocksense.dev     | admin123   |
| Storekeeper | store@stocksense.dev     | store123   |
| Viewer      | viewer@stocksense.dev    | viewer123  |

---

## Running Tests

```bash
# From the backend/ directory with venv activated:
pytest

# With coverage (if coverage is installed):
pytest --cov=app tests/
```

Tests use an in-memory SQLite database — no external services needed.

---

## Environment Variables

| Variable   | Default         | Description                                  |
|------------|-----------------|----------------------------------------------|
| `DATABASE_URL` | `sqlite:///./stocksense.db` | PostgreSQL DSN for production |
| `SECRET_KEY`   | `change-me`     | JWT signing secret — **change in production** |
| `DEBUG`        | `false`         | Enables `/dev/seed-demo` and `/dev/reset`    |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, routers, health
│   ├── config.py          # Settings from env
│   ├── database.py        # Shim → _temp/database_temp.py (swap when Member A delivers)
│   ├── models.py          # Shim → _temp/models_temp.py   (swap when Member A delivers)
│   ├── schemas.py         # All Pydantic v2 request/response models
│   ├── security.py        # bcrypt + JWT helpers
│   ├── dependencies.py    # get_current_user, require_role
│   ├── errors.py          # ApiError + global handlers
│   ├── _temp/             # ⚠️ TEMPORARY — delete when Member A delivers
│   │   ├── models_temp.py
│   │   ├── database_temp.py
│   │   └── queries_stub.py
│   ├── queries/           # Shims over Member A's query layer
│   │   ├── usage.py       # get_usage, get_daily_series, get_incoming_stock
│   │   ├── dashboard.py   # dashboard_summary, movement_chart, …
│   │   ├── reports.py     # stock_movements, inventory_valuation, stock_status
│   │   └── insights.py    # placeholder
│   ├── routers/
│   │   ├── auth.py        products.py   categories.py   suppliers.py
│   │   ├── transactions.py  forecasting.py  recommendations.py
│   │   ├── dashboard.py   reports.py   audit.py   settings.py   dev.py
│   └── services/
│       ├── inventory_service.py    # apply_movement (ONLY code that changes qty)
│       ├── forecasting_service.py  # Pure: compute_forecast
│       ├── reorder_service.py      # Pure: compute_reorder
│       ├── reporting_service.py    # CSV builder
│       ├── settings_service.py     # Key/value settings helpers
│       └── audit_service.py        # audit() helper
├── tests/
│   ├── conftest.py         # In-memory SQLite fixtures
│   ├── test_inventory.py   # Over-issue, balance_after, reversal, RBAC, duplicate SKU
│   ├── test_forecasting.py # Spec examples, insufficient_data, thresholds
│   ├── test_reorder.py     # Spec example (78 units), confidence, lead time
│   └── test_rbac.py        # All role boundaries, no-token 401
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## API Base URL

All routes under `/api/v1`. Auth via `Authorization: Bearer <jwt>`.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login → JWT token |
| GET  | `/api/v1/health` | Health check (public) |
| GET  | `/api/v1/products` | Product list with forecast state |
| POST | `/api/v1/transactions/stock-in` | Stock in |
| POST | `/api/v1/transactions/stock-out` | Stock out |
| GET  | `/api/v1/forecasts` | All product forecasts |
| GET  | `/api/v1/recommendations` | Reorder recommendations |
| GET  | `/api/v1/dashboard/summary` | Dashboard KPIs |
| GET  | `/api/v1/reports/stock-movements?format=csv` | CSV report |

Full OpenAPI spec: `/docs` or `/openapi.json`

---

## Member A Handoff Notes

⚠️ **Files to delete once Member A delivers their work:**

| Temp file | Replace with |
|-----------|-------------|
| `app/_temp/models_temp.py` | Member A's `app/models.py` |
| `app/_temp/database_temp.py` | Member A's `app/database.py` |
| `app/_temp/queries_stub.py` | Member A's `app/queries/*.py` |

**Shim files to update** (single import line change each):
- `app/models.py` — change import from `_temp.models_temp` to the real implementation
- `app/database.py` — change import from `_temp.database_temp` to the real implementation  
- `app/queries/usage.py` — change import to `app.queries.usage` (real)
- `app/queries/dashboard.py` — change import to `app.queries.dashboard` (real)
- `app/queries/reports.py` — change import to `app.queries.reports` (real)

**Query functions the backend depends on** (Member A must implement):
```python
# app/queries/usage.py
get_usage(db, product_ids: list[int], window_days: int) -> dict[int, UsageStats]
get_daily_series(db, product_id: int, days: int) -> list[dict]
get_incoming_stock(db, product_id: int) -> int

# app/queries/dashboard.py  
dashboard_summary(db) -> dict
movement_chart(db, days: int) -> list[dict]
top_used(db, days: int, limit: int) -> list[dict]
category_value(db) -> list[dict]
alerts_base(db) -> list[dict]

# app/queries/reports.py
stock_movements(db, **filters) -> list[dict]
inventory_valuation(db) -> dict
stock_status(db) -> list[dict]

# app/seed.py
seed_demo(db: Session) -> None
```

**UsageStats dataclass** (Member A should return this from `get_usage`):
```python
@dataclass
class UsageStats:
    product_id: int
    total_usage: int       # Σ |delta| of usage-type rows, minus reversed
    usage_days: int        # distinct days with usage in window
    window_days: int
    observed_days: int     # min(window_days, days since product created) ≥ 1
    avg_daily_usage: float # total_usage / observed_days
    daily_series: list[dict]  # [{date, used, received, balance}]
```
