# Inventra — Backend API

FastAPI backend for the Inventra inventory management system.  
Member A owns the database layer (`database/`). Member B owns everything here.

---

## Prerequisites

- Python 3.11+ (tested on 3.14)
- PostgreSQL 16 (production) — use Member A's `database/docker-compose.yml`
- SQLite — used automatically for local dev and all tests (no setup needed)

---

## Quick Start

```bash
# 1. Create and activate venv
cd backend
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env and configure
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY; leave DATABASE_URL as sqlite for local dev

# 4. Start the dev server (SQLite DB auto-created on first run)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API docs:** http://localhost:8000/docs  
- **Health:** http://localhost:8000/api/v1/health

---

## Switching to PostgreSQL

1. Start Postgres via Member A's docker-compose:
   ```bash
   cd ../database && docker compose up -d
   ```
2. Uncomment the `psycopg` line in `requirements.txt` and `pip install -r requirements.txt`
3. Set `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/stocksense` in `.env`
4. Run Alembic migrations (Member A's concern):
   ```bash
   alembic upgrade head
   ```

---

## Demo Logins

Seed via `POST /api/v1/dev/seed-demo` (requires `DEBUG=true` in `.env`).

| Role          | Email                 | Password   |
|---------------|-----------------------|------------|
| Admin         | admin@inventra.dev    | admin123   |
| Store Manager | store@inventra.dev    | store123   |
| Viewer        | viewer@inventra.dev   | viewer123  |

---

## Roles & Permissions

| Endpoint category        | admin | store_manager | viewer |
|--------------------------|:-----:|:-------------:|:------:|
| Login / Me               | ✅    | ✅            | ✅     |
| Read products/categories | ✅    | ✅            | ✅     |
| Create/edit products     | ✅    | ✅            | ❌     |
| Archive products         | ✅    | ❌            | ❌     |
| Stock in / out           | ✅    | ✅            | ❌     |
| Manual adjustments       | ✅    | ❌            | ❌     |
| Manage users             | ✅    | ❌            | ❌     |
| Audit logs               | ✅    | ❌            | ❌     |
| Read dashboard/forecasts | ✅    | ✅            | ✅     |
| Update settings          | ✅    | ❌            | ❌     |
| Dev endpoints            | ✅    | ❌            | ❌     |

---

## Running Tests

```bash
# From the backend/ directory with venv activated
pytest

# Verbose with short tracebacks
pytest -v --tb=short

# With coverage
pytest --cov=app tests/
```

Tests use an in-memory SQLite database — **no external services required**.  
All 45 tests pass on Python 3.14 + FastAPI 0.115 + SQLAlchemy 2.0.

---

## Environment Variables

| Variable       | Default                      | Description                                      |
|----------------|------------------------------|--------------------------------------------------|
| `DATABASE_URL` | `sqlite:///./stocksense.db`  | SQLite for dev; PostgreSQL DSN for production    |
| `SECRET_KEY`   | `change-me`                  | JWT signing secret — **must change in prod**     |
| `DEBUG`        | `false`                      | Enables `/api/v1/dev/seed-demo` and `/dev/reset` |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI app, CORS, lifespan, health, meta/enums
│   ├── config.py             # Pydantic-settings (reads .env)
│   ├── database.py           # Lazy engine, SessionLocal, get_db, create_tables
│   ├── models.py             # Member A's SQLAlchemy 2.0 models (copied + SQLite patches)
│   ├── schemas.py            # All Pydantic v2 request/response models
│   ├── security.py           # bcrypt hashing + JWT (HS256, 8 h)
│   ├── dependencies.py       # get_current_user, require_role() factory
│   ├── errors.py             # ApiError + global handlers → {detail, code, field}
│   ├── queries/              # Adapters over Member A's database/ query layer
│   │   ├── usage.py          # get_usage, get_daily_series, get_incoming_stock
│   │   ├── dashboard.py      # summary, movement_chart, top_used, category_value
│   │   └── reports.py        # stock_movements, inventory_valuation, stock_status
│   ├── routers/
│   │   ├── auth.py           # POST /auth/login, /auth/change-password, GET /auth/me
│   │   ├── users.py          # CRUD /users (admin only)
│   │   ├── categories.py     # CRUD /categories
│   │   ├── suppliers.py      # CRUD /suppliers
│   │   ├── products.py       # CRUD /products with status + forecast state
│   │   ├── transactions.py   # /stock-in, /stock-out, /adjustments, /{id}/reverse
│   │   ├── forecasting.py    # GET /forecasts, /forecasts/{id}
│   │   ├── recommendations.py# GET /recommendations, POST /simulate
│   │   ├── dashboard.py      # /summary, /alerts, /movement-chart, /top-used
│   │   ├── reports.py        # /stock-movements, /inventory-valuation, /stock-status
│   │   ├── audit.py          # GET /audit-logs (admin only)
│   │   ├── settings.py       # GET/PUT /settings
│   │   └── dev.py            # POST /seed-demo, /reset (DEBUG=true only)
│   └── services/
│       ├── inventory_service.py    # apply_movement() — ONLY code that changes qty
│       ├── forecasting_service.py  # Pure: compute_forecast()
│       ├── reorder_service.py      # Pure: compute_reorder()
│       ├── reporting_service.py    # CSV builder with formula-injection escaping
│       ├── settings_service.py     # Key/value settings read/write
│       └── audit_service.py        # audit() helper — called from every mutation
├── tests/
│   ├── conftest.py           # Single-connection SQLite fixtures, seed helpers
│   ├── test_inventory.py     # Over-issue 409, balance_after, reversal once only,
│   │                         #   duplicate SKU, adjustment, viewer 403
│   ├── test_forecasting.py   # Spec examples, insufficient_data, state thresholds
│   ├── test_reorder.py       # Spec example (78 units, $780 cost), confidence,
│   │                         #   lead time, safety stock, incoming reduces reorder
│   └── test_rbac.py          # All role boundaries, no-token 401
├── requirements.txt
├── pytest.ini
└── .env.example

database/                     # Member A's lane (do not edit)
├── models.py                 # Source of truth — copied to backend/app/models.py
├── usage.py / dashboard.py / reports.py / insights.py
├── crud.py                   # Product/category/supplier CRUD helpers
├── seed_demo.py              # seed_demo(db) — called by /dev/seed-demo
├── docker-compose.yml        # Postgres + pgAdmin
├── ledger_trigger.sql        # DB trigger: blocks UPDATE/DELETE on stock_transactions
└── alembic_trigger_migration.py
```

---

## API Quick Reference

All routes under `/api/v1`. Authenticate with `Authorization: Bearer <jwt>`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/login` | — | Login → JWT |
| `GET`  | `/auth/me` | any | Current user |
| `GET`  | `/health` | — | Health check |
| `GET`  | `/products` | any | Paginated product list |
| `POST` | `/products` | admin, store_manager | Create product |
| `POST` | `/transactions/stock-in` | admin, store_manager | Stock in |
| `POST` | `/transactions/stock-out` | admin, store_manager | Stock out |
| `POST` | `/transactions/adjustments` | admin | Set absolute qty |
| `POST` | `/transactions/{id}/reverse` | admin, store_manager | Reverse transaction |
| `GET`  | `/forecasts` | any | All product forecasts |
| `GET`  | `/recommendations` | any | Reorder recommendations |
| `POST` | `/recommendations/simulate` | any | What-if simulation |
| `GET`  | `/dashboard/summary` | any | KPI tiles |
| `GET`  | `/dashboard/alerts` | any | Low stock + forecast alerts |
| `GET`  | `/reports/stock-movements?format=csv` | any | CSV report |
| `GET`  | `/audit-logs` | admin | Audit log |
| `GET`  | `/meta/enums` | — | All enum values for frontend |

Full OpenAPI spec at `/docs` (Swagger UI) or `/redoc`.

---

## Key Design Rules

1. **`apply_movement()` is the only function that modifies `current_quantity`.**  
   All stock changes flow through `inventory_service.apply_movement()`. It handles:
   - Row locking (PostgreSQL) / dialect detection (SQLite skip)
   - Non-negative quantity guard → `409 INSUFFICIENT_STOCK`
   - Idempotency via `client_request_id`
   - Audit logging

2. **Pure business logic in services.**  
   `forecasting_service` and `reorder_service` take plain Python values and return dataclasses — no DB access, fully unit-testable without fixtures.

3. **Passwords never leak.**  
   `password_hash` is excluded from all `UserOut` schemas.

4. **CSV injection escaping.**  
   `reporting_service.build_csv` prefixes cells starting with `=`, `+`, `-`, `@` with a tab.
