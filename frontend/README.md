# Inventra — Frontend

React 18 + Vite 8 SPA for the Inventra inventory management system.

---

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

App runs at **http://localhost:5173**

> The backend must be running on port 8000. See the [root README](../README.md).

---

## Demo Accounts

Seed data first:
```bash
curl -X POST http://localhost:8000/api/v1/dev/seed-demo
```
(requires `DEBUG=true` in `backend/.env`)

| Role | Email | Password |
|---|---|---|
| Admin | admin@inventra.dev | admin123 |
| Store Manager | store@inventra.dev | store123 |
| Viewer | viewer@inventra.dev | viewer123 |

---

## Environment

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend base URL |

Edit `frontend/.env` to point at a different backend.

---

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.js        # fetch wrapper: JWT injection, 401 redirect, error class
│   │   └── index.js         # domain modules: Auth, Products, Dashboard, etc.
│   ├── context/
│   │   └── AuthContext.jsx  # JWT session, login/logout, isAdmin/canWrite helpers
│   ├── components/
│   │   ├── Layout.jsx       # Sidebar + topbar shell
│   │   ├── Sidebar.jsx      # Role-aware navigation
│   │   └── ui.jsx           # Badge, Modal, StatCard, Toast, Empty, Confirm…
│   ├── hooks/
│   │   └── useToast.js      # Auto-dismiss toast notifications
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Products.jsx
│   │   ├── Transactions.jsx
│   │   ├── Forecasts.jsx
│   │   ├── Recommendations.jsx
│   │   ├── Categories.jsx
│   │   ├── Suppliers.jsx
│   │   ├── Reports.jsx
│   │   ├── Settings.jsx
│   │   ├── Users.jsx        # admin only
│   │   └── Audit.jsx        # admin only
│   ├── App.jsx              # Router + auth guards
│   ├── main.jsx             # React entry point
│   └── index.css            # Design system (dark mode, purple brand)
├── public/                  # SVG assets
├── .env                     # VITE_API_URL
├── vite.config.js
└── package.json
```

---

## Pages

| Route | Description | Roles |
|---|---|---|
| `/login` | JWT auth + demo quick-fill | public |
| `/` | Dashboard: KPI tiles, area/donut charts, alerts | all |
| `/products` | Searchable list, create/edit modal, archive | all / write |
| `/transactions` | Stock in/out/adjust/reverse, type filter | all / write |
| `/forecasts` | Stockout predictions, trend icons, window filter | all |
| `/recommendations` | Reorder suggestions, cost banner, simulate modal | all |
| `/categories` | CRUD | all / write |
| `/suppliers` | CRUD with lead time & active status | all / write |
| `/reports` | Movements / valuation / status + CSV export | all |
| `/settings` | Forecast & reorder thresholds | all / admin |
| `/users` | Create/edit/delete users, role badges | admin |
| `/audit` | Filterable audit event log | admin |

---

## Auth Flow

1. `Auth.login(email, password)` → `POST /api/v1/auth/login`
2. JWT stored in `sessionStorage` under key `inventraUser`
3. Every request adds `Authorization: Bearer <token>`
4. On 401 → clear session + redirect to `/login`

---

## CORS Notes

The backend whitelist includes ports **5173, 5174, 5175** (Vite defaults + fallbacks).  
If you run Vite on a different port, add it to `CORS_ORIGINS` in `backend/app/config.py`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `react` + `react-dom` | UI framework |
| `react-router-dom` | Client-side routing |
| `recharts` | Area, bar, pie charts on Dashboard |
| `lucide-react` | Icon set |
| `vite` + `@vitejs/plugin-react` | Build tooling |
