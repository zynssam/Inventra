# Inventra

> Inventory management — track smarter, restock earlier.

A full-stack inventory management system with real-time stock tracking, AI-powered forecasting, reorder recommendations, and role-based access control.

---

## Repository Structure

```
Inventra/
├── backend/          # FastAPI backend API (Member B)
├── frontend/         # React + Vite frontend SPA (Member C)
├── database/         # SQLAlchemy models, queries, migrations (Member A)
├── architecture.md   # System design & API contract
├── features.md       # Feature list & priorities
└── README.md         # ← you are here
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 8, React Router v6, Recharts, lucide-react |
| Backend | Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 (prod) / SQLite (local dev & tests) |
| Auth | JWT (HS256, 8 h expiry) + bcrypt |
| Migrations | Alembic |

---

## Quick Start — Full Stack

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone the repo

```bash
git clone https://github.com/zynssam/Inventra.git
cd Inventra
```

### 2. Start the backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and DEBUG=true for local dev

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API live at **http://localhost:8000** · Swagger docs at **http://localhost:8000/docs**

### 3. Seed demo data

With `DEBUG=true` in `backend/.env`:

```bash
curl -X POST http://localhost:8000/api/v1/dev/seed-demo
```

Creates demo users, products, categories, suppliers, and stock transactions.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

App live at **http://localhost:5173**

> **Note:** If port 5173 is taken, Vite falls back to 5174/5175 — all three are whitelisted in the backend CORS config.

### 5. Sign in

| Role | Email | Password |
|---|---|---|
| Admin | admin@inventra.dev | admin123 |
| Store Manager | store@inventra.dev | store123 |
| Viewer | viewer@inventra.dev | viewer123 |

> These accounts are created by the seed step. The login page has a **"Try a demo account"** quick-fill button.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -v --tb=short
```

Tests use an in-memory SQLite database — no external services needed.  
**45 tests, all passing.**

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./inventra.db` | SQLite for dev; Postgres DSN for prod |
| `SECRET_KEY` | `change-me` | JWT signing secret — **change in prod** |
| `DEBUG` | `false` | Enables `/dev/seed-demo` and `/dev/reset` |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend base URL |

---

## Frontend Pages

| Route | Page | Access |
|---|---|---|
| `/login` | Sign in | public |
| `/` | Dashboard — KPIs, charts, alerts | all |
| `/products` | Product list + CRUD | all / admin+manager |
| `/transactions` | Stock in/out/adjust/reverse | all / admin+manager |
| `/forecasts` | Stockout forecasts | all |
| `/recommendations` | Reorder recommendations + simulate | all |
| `/categories` | Category management | all / admin+manager |
| `/suppliers` | Supplier management | all / admin+manager |
| `/reports` | Stock reports + CSV export | all |
| `/settings` | Forecast thresholds | all / admin |
| `/users` | User management | admin only |
| `/audit` | Audit log | admin only |

---

## Team Lanes

| Member | Owns |
|---|---|
| **Member A** | `database/` — models, migrations, queries, docker-compose, seed |
| **Member B** | `backend/` — FastAPI app, auth, routers, services, tests |
| **Member C** | `frontend/` — React SPA, API client, UI components |

---

## Branches

| Branch | Purpose |
|---|---|
| `main` | Stable merged code |
| `features/backend-v2` | Current integrated backend + frontend |
| `features/database` | Member A's database layer |
| `features/frontend-1` | Member C's original HTML prototype |

---

## API Overview

All routes under `/api/v1` · Auth via `Authorization: Bearer <token>`

| Method | Path | Roles | Description |
|---|---|---|---|
| `POST` | `/auth/login` | — | Login → JWT |
| `GET` | `/auth/me` | any | Current user info |
| `GET` | `/products` | any | Product list + forecast state |
| `POST` | `/products` | admin, store_manager | Create product |
| `POST` | `/transactions/stock-in` | admin, store_manager | Stock in |
| `POST` | `/transactions/stock-out` | admin, store_manager | Stock out |
| `POST` | `/transactions/adjustments` | admin | Manual quantity adjustment |
| `POST` | `/transactions/:id/reverse` | admin, store_manager | Reverse a transaction |
| `GET` | `/forecasts` | any | Stockout forecasts |
| `GET` | `/recommendations` | any | Reorder recommendations |
| `POST` | `/recommendations/simulate` | any | What-if simulation |
| `GET` | `/dashboard/summary` | any | KPI tiles |
| `GET` | `/dashboard/alerts` | any | Low stock + forecast alerts |
| `GET` | `/reports/stock-movements` | any | Movement report (JSON/CSV) |
| `GET` | `/reports/inventory-valuation` | any | Valuation report (JSON/CSV) |
| `GET` | `/audit-logs` | admin | Full audit trail |
| `PUT` | `/settings` | admin | Update forecast settings |
| `GET` | `/meta/enums` | — | Enum values for frontend |

Full OpenAPI spec: **http://localhost:8000/docs**
