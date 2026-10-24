# StockSense — Architecture

> Track Smarter. Restock Earlier. Never Run Out.

This document is the technical blueprint for the prototype: stack, data model, business rules, the **complete API contract for the frontend**, and the **backend build steps**. Features and priorities live in `features.md`.

---

## 1. Design principles

1. **The database is the source of truth.** The browser never computes stock quantities.
2. **Every stock change is a ledger row.** `stock_transactions` is append-only; `products.current_quantity` is a cached running balance that must always equal the sum of the ledger (checked by a reconciliation endpoint).
3. **Atomic movements.** Ledger insert + quantity update + audit log happen in one DB transaction with a row lock on the product.
4. **Rules-based and explainable.** Every forecast and recommendation returns its inputs and a human-readable `explanation`. No hidden "AI".
5. **Permissions live in the backend.** The UI only hides things for convenience.
6. **Never invent data.** Too little history → `insufficient_data`, not a made-up number.

---

## 2. Stack (prototype choices)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React + Vite, Tailwind, React Router, Recharts, `qrcode`, `html5-qrcode` | Add TanStack Query for fetching/caching |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic | Auto OpenAPI docs at `/docs` |
| Database | PostgreSQL 16 | `DATABASE_URL` env var. SQLite works for quick local dev (skip `FOR UPDATE`) |
| Auth | JWT (HS256), bcrypt via `passlib` | 8-hour access token, no refresh token in prototype |
| Tests | Pytest + httpx `TestClient` | Focus tests on stock logic and RBAC |
| Dev | `docker-compose.yml` (db + api + web) | One command demo setup |

---

## 3. System diagram

```
 Admin / Storekeeper / Viewer
            │
            ▼
┌──────────────────────────────────────────────┐
│ FRONTEND — React + Vite                      │
│  Pages: Login · Dashboard · Products ·       │
│  Product Detail · Stock Movements · Scan ·   │
│  Stocktake · Restocking · Purchase Orders ·  │
│  Suppliers/Categories · Reports · Settings   │
│  services/api.js  (axios + JWT interceptor)  │
└───────────────────────┬──────────────────────┘
                        │ HTTPS / JSON  (/api/v1)
                        ▼
┌──────────────────────────────────────────────┐
│ BACKEND — FastAPI                            │
│  Routers  → thin: parse, auth, call service  │
│  Services → business logic                   │
│    inventory_service    (atomic movements)   │
│    forecasting_service  (usage, days left)   │
│    reorder_service      (qty, explanations)  │
│    insight_service      (anomaly, dead stock)│
│    stocktake_service    po_service           │
│    reporting_service    audit_service        │
│  Dependencies: get_current_user, require_role│
└───────────────────────┬──────────────────────┘
                        │ SQLAlchemy
                        ▼
┌──────────────────────────────────────────────┐
│ POSTGRESQL                                   │
│ users · products · categories · suppliers ·  │
│ stock_transactions · purchase_orders(+items) │
│ stocktakes(+lines) · settings · audit_logs   │
└──────────────────────────────────────────────┘
```

**Smart features share one data source:** forecasting, reorder, anomalies and the dashboard all read `stock_transactions` + `products` through the same usage query. Nothing keeps a separate copy.

---

## 4. Atomic stock movement (the core rule)

```python
def apply_movement(db, user, product_id, delta, tx_type, reason, **refs):
    with db.begin():                                   # one DB transaction
        p = db.execute(
            select(Product).where(Product.id == product_id).with_for_update()
        ).scalar_one()                                 # row lock: no race conditions
        if p.is_archived:
            raise ApiError(409, "PRODUCT_ARCHIVED")
        new_qty = p.current_quantity + delta
        if new_qty < 0:
            raise ApiError(409, "INSUFFICIENT_STOCK",
                           f"Only {p.current_quantity} {p.unit} available")
        p.current_quantity = new_qty
        tx = StockTransaction(product_id=p.id, type=tx_type, quantity_delta=delta,
                              balance_after=new_qty, user_id=user.id,
                              reason=reason, **refs)
        db.add(tx)
        audit(db, user, "STOCK_" + tx_type.upper(), "product", p.id,
              {"delta": delta, "balance_after": new_qty, "tx_id": tx.id})
    return tx
```

Extra safeguards:
- DB `CHECK (current_quantity >= 0)` as a second line of defence.
- Optional `client_request_id` (unique) on POST movements → double-click / retry safe (idempotent).
- Completed transactions are **never updated or deleted**. Mistakes are fixed with a **reversal** (a new row with the opposite delta, `reference_id` → original) or an **adjustment**.

---

## 5. Data model

All timestamps are `timestamptz` stored in UTC. Money is `NUMERIC(12,2)`. Quantities are integers in the prototype (switch to `NUMERIC(12,3)` for litres/kg later).

### users
`id` · `name` · `email` (unique) · `password_hash` · `role` (`admin|storekeeper|viewer`) · `is_active` (bool) · `created_at`

### categories
`id` · `name` (unique) · `description`

### suppliers
`id` · `name` · `contact_person` · `phone` · `email` · `address` · `is_archived` · `created_at`

### products
`id` · `name` · `sku` (unique, indexed) · `category_id` FK · `default_supplier_id` FK (nullable) · `unit` · `current_quantity` (CHECK ≥ 0) · `minimum_stock` · `unit_cost` · `selling_price` (nullable) · `lead_time_days` (default 0) · `safety_stock` (default 0) · `target_days` (nullable → falls back to global setting) · `location` (nullable, e.g. "Shelf B2") · `is_archived` (bool, replaces hard delete) · `created_at` · `updated_at`

### stock_transactions (append-only ledger)
`id` · `product_id` FK (indexed) · `type` · `quantity_delta` (signed, non-zero) · `balance_after` · `user_id` FK · `supplier_id` FK (nullable) · `recipient` (text, nullable — person/department/customer) · `reason` · `reference_id` (nullable: original tx for reversals) · `purchase_order_id` (nullable) · `client_request_id` (nullable, unique) · `created_at` (indexed)

`type` values and whether they count as **usage** for forecasting:

| type | delta | counts as usage? |
|---|---|---|
| `purchase` | + | no |
| `return_in` (returned to stock) | + | no (but see note) |
| `sale` | − | **yes** |
| `issue` (lab issue) | − | **yes** |
| `consumption` | − | **yes** |
| `adjustment` | ± | no |
| `reversal` | opposite of original | cancels the original from usage if original was a usage type |

> Note: a `return_in` linked to an earlier usage transaction can optionally net against usage. Keep it out of the prototype unless time allows.

### purchase_orders
`id` · `po_number` (unique, e.g. `PO-2026-0001`) · `supplier_id` FK · `status` (`draft|ordered|partially_received|received|cancelled`) · `order_date` · `expected_date` · `notes` · `created_by` FK · `created_at`

### purchase_order_items
`id` · `purchase_order_id` FK · `product_id` FK · `quantity_ordered` · `quantity_received` (default 0) · `unit_cost`

**Incoming stock** for a product = `Σ (quantity_ordered − quantity_received)` over items whose PO status is `ordered` or `partially_received`. Drafts do **not** count.

### stocktakes / stocktake_lines
`stocktakes`: `id` · `name` · `status` (`in_progress|finalized|cancelled`) · `started_by` · `started_at` · `finalized_at`
`stocktake_lines`: `id` · `stocktake_id` FK · `product_id` FK · `system_quantity` (snapshot at scan time) · `counted_quantity` · `scanned_by` · `scanned_at` — unique `(stocktake_id, product_id)`

### settings (single key/value table)
| key | default | meaning |
|---|---|---|
| `default_target_days` | 20 | coverage target |
| `usage_window_days` | 14 | observation window |
| `min_usage_days` | 3 | min. distinct days with usage to trust a forecast |
| `warning_days` | 14 | forecast warning threshold |
| `critical_days` | 7 | forecast critical threshold |
| `currency` | `INR` | display only |
| `org_name` | `StockSense` | display only |

### audit_logs
`id` · `user_id` FK · `action` · `entity_type` · `entity_id` · `details` (JSONB: before/after) · `created_at`

### Indexes
`products(sku)`, `products(category_id)`, `stock_transactions(product_id, created_at DESC)`, `stock_transactions(created_at)`, `stock_transactions(type)`, `audit_logs(entity_type, entity_id)`.

---

## 6. Business rules & formulas

### 6.1 Stock status (per product)
```
out_of_stock : current_quantity == 0
low_stock    : 0 < current_quantity <= minimum_stock
healthy      : current_quantity >  minimum_stock
```

### 6.2 Average daily usage
```
window      = settings.usage_window_days            (e.g. 14)
observed    = min(window, days since product was created)  (≥ 1)
total_usage = Σ |delta| of usage-type OUT rows in the window − usage reversed in the window
avg_daily   = total_usage / observed
```
Divide by the **whole window**, not just the days that had a transaction, otherwise usage is overstated.

**Sufficient data** ⇔ distinct days with usage in window ≥ `min_usage_days` **and** `total_usage > 0`. Otherwise forecast state is `insufficient_data` (some usage but too little) or `no_recent_usage` (none).

### 6.3 Forecast
```
days_until_stockout = current_quantity / avg_daily
state = critical  if days <= critical_days
        warning   if days <= warning_days
        ok        otherwise
projected_stockout_date = today + days_until_stockout
```
`current_quantity == 0` → `out_of_stock` state, days = 0.

### 6.4 Reorder recommendation
```
coverage_days = product.target_days ?? settings.default_target_days
target_stock  = avg_daily × (coverage_days + product.lead_time_days) + product.safety_stock
incoming      = Σ open PO (ordered − received)
reorder_qty   = max(0, ceil(target_stock − current_quantity − incoming))
estimated_cost = reorder_qty × unit_cost
```
With `lead_time_days = 0` and `safety_stock = 0` this is exactly the original spec formula.

Example: usage 5/day, target 20 d, stock 12, incoming 10 → `max(0, 5×20 − 12 − 10) = 78`.

Every recommendation returns:
```json
{
  "reorder_qty": 78,
  "explanation": "Uses 5.0/day over the last 14 days. For 20 days of cover you need 100 units. You have 12 on hand and 10 on order, so order 78.",
  "inputs": { "avg_daily_usage": 5.0, "window_days": 14, "target_days": 20,
              "lead_time_days": 0, "safety_stock": 0, "current": 12, "incoming": 10 },
  "confidence": "high|medium|low"
}
```
`confidence`: `high` ≥ 7 usage days in window, `medium` 3–6, `low` otherwise (low → returned with a "limited data" note, qty still computed only if state is not `insufficient_data`).

### 6.5 Anomaly flag (simple, explainable)
For each product, over the usage window: flag when the last 24 h usage `> mean_daily + 2 × std_dev` **and** `> 0`, or when one transaction is `> 3 ×` the product's median transaction size. Returned with the numbers used. Useful for spotting typos (500 instead of 5) and unusual consumption.

### 6.6 Dead stock
Products with `current_quantity > 0` and **no usage** in the last N days (default 60). Reports tied-up value.

### 6.7 Inventory health score (0–100, dashboard)
`100 × (healthy_products + 0.5 × low_stock_products) / total_active_products`, shown with the formula in a tooltip.

---

## 7. Roles & permissions

| Capability | Admin | Storekeeper | Viewer |
|---|:-:|:-:|:-:|
| View dashboard, products, transactions, reports, forecasts, recommendations | ✅ | ✅ | ✅ |
| Create / edit products, categories, suppliers | ✅ | ✅ | ❌ |
| Archive / restore products, categories, suppliers | ✅ | ❌ | ❌ |
| Stock in / stock out | ✅ | ✅ | ❌ |
| Adjustments, reversals | ✅ | ❌ | ❌ |
| Purchase orders: create / submit / receive | ✅ | ✅ | ❌ |
| Purchase orders: cancel | ✅ | ❌ | ❌ |
| Stocktake: run / scan | ✅ | ✅ | ❌ |
| Stocktake: finalize (creates adjustments) | ✅ | ❌ | ❌ |
| CSV export | ✅ | ✅ | ✅ |
| Audit logs, users, settings, dev tools | ✅ | ❌ | ❌ |

Implemented as `Depends(require_role("admin", "storekeeper"))` on each route.

---

## 8. API contract

**Base URL:** `/api/v1` · **Auth:** `Authorization: Bearer <jwt>` on everything except login & health · **Format:** JSON, UTC ISO-8601 datetimes.

**Roles column:** `A` admin · `S` storekeeper · `V` viewer. `A/S/V` = any logged-in user.

**Pagination** (list endpoints): `?page=1&page_size=20` → `{ "items": [...], "total": 134, "page": 1, "page_size": 20 }`

**Error shape:**
```json
{ "detail": "Only 4 pcs available", "code": "INSUFFICIENT_STOCK", "field": null }
```
Common codes: `INVALID_CREDENTIALS`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `DUPLICATE_SKU`, `INSUFFICIENT_STOCK`, `PRODUCT_ARCHIVED`, `HAS_DEPENDENCIES`, `INVALID_STATE`, `ALREADY_REVERSED`.

### 8.1 Auth
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/auth/login` | public | Body `{email, password}` → `{access_token, token_type, user}` |
| GET | `/auth/me` | A/S/V | Current user + role |
| POST | `/auth/change-password` | A/S/V | Body `{old_password, new_password}` |

### 8.2 Users (admin)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/users` | A | List users |
| POST | `/users` | A | Create `{name, email, password, role}` |
| GET | `/users/{id}` | A | Get one |
| PATCH | `/users/{id}` | A | Update name/role/`is_active`; reset password |

### 8.3 Categories
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/categories` | A/S/V | List with `product_count` |
| POST | `/categories` | A/S | Create |
| PATCH | `/categories/{id}` | A/S | Update |
| DELETE | `/categories/{id}` | A | Blocked with `HAS_DEPENDENCIES` if products exist |

### 8.4 Suppliers
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/suppliers` | A/S/V | List; `?q=&include_archived=` |
| POST | `/suppliers` | A/S | Create |
| GET | `/suppliers/{id}` | A/S/V | Details + totals (products supplied, total purchased value) |
| PATCH | `/suppliers/{id}` | A/S | Update |
| DELETE | `/suppliers/{id}` | A | Archive (soft) |
| GET | `/suppliers/{id}/products` | A/S/V | Products linked to supplier |
| GET | `/suppliers/{id}/transactions` | A/S/V | Purchase history from this supplier |
| GET | `/suppliers/{id}/purchase-orders` | A/S/V | POs for this supplier |

### 8.5 Products
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/products` | A/S/V | Query: `q` (name/SKU), `category_id`, `supplier_id`, `status` (`healthy|low_stock|out_of_stock`), `sort` (`name|sku|current_quantity|unit_cost|updated_at`), `order` (`asc|desc`), `include_archived`, pagination. Each row includes `status`, `days_until_stockout`, `forecast_state` |
| POST | `/products` | A/S | Create (unique SKU; optional `initial_quantity` creates an opening-balance `adjustment` ledger row) |
| GET | `/products/{id}` | A/S/V | Full details **plus** embedded `forecast` and `recommendation` objects |
| PATCH | `/products/{id}` | A/S | Update fields (quantity cannot be edited here — use movements) |
| DELETE | `/products/{id}` | A | Archive (soft delete) |
| POST | `/products/{id}/restore` | A | Un-archive |
| GET | `/products/lookup?code=` | A/S/V | **QR/SKU lookup**: accepts scanned payload `SS:{sku}`, a raw SKU, or numeric ID → product (404 if none) |
| GET | `/products/{id}/qr-payload` | A/S/V | Returns `{ "payload": "SS:LAB-0012" }` — the frontend renders the QR with `qrcode` |
| GET | `/products/{id}/transactions` | A/S/V | Movement history for the product (paginated, filter by `type`, dates) |
| GET | `/products/{id}/usage?days=30` | A/S/V | Daily usage series for charts: `[{date, used, received, balance}]` |
| POST | `/products/import` | A/S | CSV upload (multipart); `?dry_run=true` returns validation result without saving |
| GET | `/products/import-template` | A/S | Download CSV template |

Product list row example:
```json
{ "id": 7, "name": "Ethanol 500ml", "sku": "LAB-0012", "category": {"id":2,"name":"Chemicals"},
  "unit": "bottle", "current_quantity": 24, "minimum_stock": 10, "unit_cost": "180.00",
  "status": "healthy", "forecast_state": "warning", "days_until_stockout": 6.0 }
```

### 8.6 Stock movements
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/transactions/stock-in` | A/S | `{product_id, quantity, type: "purchase"\|"return_in", supplier_id?, reason, purchase_order_id?, client_request_id?}` |
| POST | `/transactions/stock-out` | A/S | `{product_id, quantity, type: "sale"\|"issue"\|"consumption", recipient?, reason, client_request_id?}` → `409 INSUFFICIENT_STOCK` if too much |
| POST | `/transactions/adjustments` | A | `{product_id, new_quantity \| delta, reason}` — reason is mandatory |
| POST | `/transactions/{id}/reverse` | A | `{reason}` — creates a reversal row; `ALREADY_REVERSED` if repeated; fails with `INSUFFICIENT_STOCK` if reversing would go negative |
| GET | `/transactions` | A/S/V | Global history. Filters: `product_id`, `type`, `user_id`, `supplier_id`, `date_from`, `date_to`, `q`, pagination |
| GET | `/transactions/{id}` | A/S/V | One entry, with reversal link if any |

Response of a movement includes `balance_after` and the updated `product` summary so the UI can refresh without a refetch.

### 8.7 Forecasting
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/forecasts` | A/S/V | Forecast for all active products. Filters: `state` (`critical|warning|ok|insufficient_data|no_recent_usage|out_of_stock`), `window_days` (override), `sort=days_until_stockout` |
| GET | `/forecasts/{product_id}` | A/S/V | Single forecast |

```json
{ "product_id": 7, "current_quantity": 24, "avg_daily_usage": 4.0, "window_days": 14,
  "usage_days_observed": 9, "days_until_stockout": 6.0,
  "projected_stockout_date": "2026-10-30", "state": "warning",
  "explanation": "24 in stock ÷ 4.0/day (14-day average) ≈ 6 days left.", "trend": "rising" }
```
`trend` = compares usage of the most recent half of the window to the earlier half (`rising|steady|falling`).

### 8.8 Recommendations / restocking
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/recommendations` | A/S/V | Products needing restock (`reorder_qty > 0`). Query: `target_days`, `window_days`, `supplier_id`, `category_id`, `include_all=true`. Returns `total_estimated_cost` too |
| GET | `/recommendations/{product_id}` | A/S/V | Single recommendation with `explanation` + `inputs` |
| POST | `/recommendations/simulate` | A/S/V | **What-if**: body `{target_days, window_days?, lead_time_days?, safety_days?}` → same list + total cost, without saving anything |
| POST | `/recommendations/draft-pos` | A/S | Body `{items:[{product_id, quantity}]}` → creates **one draft PO per supplier** (grouped by `default_supplier_id`; products without a supplier are returned in `skipped`) |

### 8.9 Purchase orders
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/purchase-orders` | A/S/V | Filters `status`, `supplier_id`, dates |
| POST | `/purchase-orders` | A/S | `{supplier_id, expected_date, notes, items:[{product_id, quantity_ordered, unit_cost}]}` → `draft` |
| GET | `/purchase-orders/{id}` | A/S/V | With items and receive progress |
| PATCH | `/purchase-orders/{id}` | A/S | Edit while `draft` only |
| POST | `/purchase-orders/{id}/submit` | A/S | `draft → ordered` (now counts as incoming stock) |
| POST | `/purchase-orders/{id}/receive` | A/S | `{items:[{item_id, quantity_received}]}` → creates `purchase` stock-in ledger rows atomically, updates status to `partially_received` / `received` |
| POST | `/purchase-orders/{id}/cancel` | A | Allowed in `draft|ordered` |

### 8.10 Stocktake (QR cycle count)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/stocktakes` | A/S | List sessions |
| POST | `/stocktakes` | A/S | Start `{name}` |
| GET | `/stocktakes/{id}` | A/S | Session with lines, variance per product, and **uncounted products list** |
| POST | `/stocktakes/{id}/scan` | A/S | `{code, counted_quantity}` — `code` is a scanned QR/SKU; upserts the line, snapshots `system_quantity` |
| POST | `/stocktakes/{id}/finalize` | A | Creates one `adjustment` per non-zero variance (reason = "Stocktake {name}"), locks the session |
| POST | `/stocktakes/{id}/cancel` | A/S | Discard |

### 8.11 Dashboard
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/dashboard/summary` | A/S/V | `{total_products, total_units, low_stock_count, out_of_stock_count, total_inventory_value, critical_forecast_count, health_score}` |
| GET | `/dashboard/movement-chart?days=30` | A/S/V | `[{date, stock_in, stock_out}]` |
| GET | `/dashboard/top-used?days=30&limit=5` | A/S/V | Most-used products |
| GET | `/dashboard/alerts` | A/S/V | Out-of-stock, low-stock, critical-forecast, anomaly items in one list with `severity` |
| GET | `/dashboard/recent-transactions?limit=10` | A/S/V | Latest movements |
| GET | `/dashboard/category-value` | A/S/V | Inventory value by category (pie/bar) |

### 8.12 Insights
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/insights/anomalies` | A/S/V | Unusual usage / outlier transactions with numbers shown |
| GET | `/insights/dead-stock?days=60` | A/S/V | Stock with no usage, plus value tied up |
| GET | `/insights/abc` | A/S/V | A/B/C classification by annual-usage value (A = top 80%, B = next 15%, C = last 5%) |
| GET | `/insights/reconciliation` | A | Compares `current_quantity` with ledger sum per product; lists mismatches (should always be empty) |

### 8.13 Reports (all support `?format=json` (default) or `?format=csv`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/reports/stock-movements` | A/S/V | `date_from`, `date_to`, `product_id`, `category_id`, `type`, `user_id` |
| GET | `/reports/inventory-valuation` | A/S/V | Per product qty × cost, subtotals by category, grand total |
| GET | `/reports/stock-status` | A/S/V | Healthy / low / out-of-stock listing |
| GET | `/reports/restock-plan` | A/S/V | Current recommendations as exportable report |
| GET | `/reports/supplier-purchases` | A/S/V | Purchases per supplier in a date range |

CSV responses use `Content-Disposition: attachment; filename="stock-movements_2026-10-24.csv"`.

### 8.14 Audit, settings, meta, dev
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/audit-logs` | A | Filters `user_id`, `action`, `entity_type`, `entity_id`, dates |
| GET | `/settings` | A/S/V | All settings (read so UI can show thresholds) |
| PUT | `/settings` | A | Update settings (validated, e.g. `critical_days < warning_days`) |
| GET | `/meta/enums` | A/S/V | Transaction types, roles, statuses, units — keeps dropdowns in sync |
| GET | `/health` | public | `{status:"ok", db:"ok"}` |
| POST | `/dev/seed-demo` | A | Only when `DEBUG=true`: wipes demo data and creates users, categories, suppliers, ~25 products with **30 days of realistic usage history**, one open PO |
| POST | `/dev/reset` | A | Only when `DEBUG=true`: clears all data |

**Total: ~80 endpoint operations.** P0 subset needed for the core demo is marked in `features.md`.

---

## 9. Frontend page → endpoint map

| Page | Endpoints used |
|---|---|
| Login | `POST /auth/login`, `GET /auth/me` |
| Dashboard | `/dashboard/summary`, `/dashboard/movement-chart`, `/dashboard/top-used`, `/dashboard/alerts`, `/dashboard/recent-transactions`, `/dashboard/category-value` |
| Products list | `GET /products`, `GET /categories`, `GET /suppliers`, `POST /products/import` |
| Product form | `POST/PATCH /products`, `GET /categories`, `GET /suppliers`, `GET /meta/enums` |
| Product detail | `GET /products/{id}`, `/products/{id}/transactions`, `/products/{id}/usage`, `/products/{id}/qr-payload`, stock-in/out/adjust endpoints |
| Stock movements | `GET /transactions`, `POST /transactions/stock-in`, `/stock-out`, `/adjustments`, `/{id}/reverse` |
| Scan (QR) | `GET /products/lookup?code=` → then stock-in/out |
| Stocktake | `/stocktakes` family |
| Restocking | `/forecasts`, `/recommendations`, `/recommendations/simulate`, `/recommendations/draft-pos` |
| Purchase orders | `/purchase-orders` family |
| Suppliers & Categories | `/suppliers` family, `/categories` family |
| Insights | `/insights/*` |
| Reports | `/reports/*` (+ CSV download) |
| Users & Settings | `/users`, `/settings`, `/audit-logs`, `/dev/seed-demo` |

---

## 10. Backend folder structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, router include, error handlers
│   ├── config.py            # Settings from env (DATABASE_URL, SECRET_KEY, DEBUG)
│   ├── database.py          # engine, SessionLocal, Base, get_db
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic request/response models
│   ├── security.py          # hash/verify password, create/decode JWT
│   ├── dependencies.py      # get_current_user, require_role
│   ├── errors.py            # ApiError + handlers
│   ├── routers/
│   │   ├── auth.py  users.py  categories.py  suppliers.py  products.py
│   │   ├── transactions.py  forecasting.py  recommendations.py
│   │   ├── purchase_orders.py  stocktakes.py  dashboard.py
│   │   ├── insights.py  reports.py  audit.py  settings.py  dev.py
│   └── services/
│       ├── inventory_service.py     # apply_movement, reverse, adjust
│       ├── usage_service.py         # shared usage query (used by all smart features)
│       ├── forecasting_service.py
│       ├── reorder_service.py
│       ├── insight_service.py
│       ├── po_service.py
│       ├── stocktake_service.py
│       ├── reporting_service.py     # CSV/JSON builders
│       ├── audit_service.py
│       └── seed_service.py
├── alembic/  alembic.ini
├── tests/
│   ├── test_inventory.py   test_forecasting.py   test_reorder.py
│   ├── test_rbac.py        test_purchase_orders.py   test_stocktake.py
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## 11. Backend build steps

Each step ends in something you can verify in Swagger (`/docs`) before moving on. The frontend can start against this contract as soon as Step 3 is done.

### Step 0 — Project skeleton *(~1 h)*
- Create `backend/` structure, virtualenv, `requirements.txt` (fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pydantic-settings, passlib[bcrypt], python-jose, python-multipart, pytest, httpx).
- `docker-compose.yml` with Postgres; `.env` with `DATABASE_URL`, `SECRET_KEY`, `DEBUG`.
- `main.py` with CORS for the Vite dev origin, `GET /api/v1/health`, global `ApiError` handler.
- ✅ **Done when:** `/docs` opens and `/health` returns `db: ok`.

### Step 1 — Models & migrations *(~1.5 h)*
- Implement every table from §5 with FKs, unique SKU, `CHECK (current_quantity >= 0)`, indexes.
- Alembic initial migration.
- ✅ **Done when:** `alembic upgrade head` creates all tables cleanly on an empty DB.

### Step 2 — Auth & RBAC *(~1.5 h)*
- `security.py` (bcrypt, JWT 8 h), `dependencies.py` (`get_current_user`, `require_role`).
- Endpoints: `/auth/login`, `/auth/me`, `/auth/change-password`, `/users` CRUD.
- Seed script creates `admin@stocksense.dev`, `store@…`, `viewer@…` demo users.
- ✅ **Done when:** a viewer token gets `403` on a protected admin route, and no token gets `401`.

### Step 3 — Master data CRUD *(~2 h)*
- Categories, suppliers, products (list with search / filter / sort / pagination, create, patch, archive, restore).
- Product `status` computed in the query/serializer; `DUPLICATE_SKU` error.
- `/products/lookup`, `/products/{id}/qr-payload`, `/meta/enums`, `/settings` GET/PUT.
- ✅ **Done when:** you can create a product, find it by SKU via `lookup`, and archive it. **Hand the contract to the frontend now.**

### Step 4 — Inventory ledger *(~3 h, most important step)*
- `inventory_service.apply_movement` exactly as in §4.
- `/transactions/stock-in`, `/stock-out`, `/adjustments`, `/{id}/reverse`, list & detail, `/products/{id}/transactions`.
- Opening balance on product create becomes an `adjustment` row.
- Tests: over-issue rejected, balance_after correct, reversal works once only, two concurrent issues can't overdraw, viewer is forbidden.
- ✅ **Done when:** all inventory tests pass and `/insights/reconciliation` (add a stub now) shows zero mismatches.

### Step 5 — Audit logging *(~45 min)*
- `audit_service.audit()` called from products, suppliers, users, settings, and every movement.
- `/audit-logs` (admin).
- ✅ **Done when:** each create/update/stock action produces one log row with user, timestamp and before/after details.

### Step 6 — Usage, forecast & reorder engines *(~3 h)*
- `usage_service.get_usage(db, product_ids, window_days)` — one grouped SQL query returning `total_usage`, `usage_days`, daily series, handling reversals.
- `forecasting_service` (§6.2–6.3), `reorder_service` (§6.4) incl. incoming PO quantity, explanation strings, confidence.
- Endpoints: `/forecasts`, `/forecasts/{id}`, `/recommendations`, `/recommendations/{id}`, `/recommendations/simulate`, `/products/{id}/usage`. Embed `forecast` + `recommendation` in `GET /products/{id}`.
- Tests: your spec examples (24 ÷ 4 = 6 days; 78-unit reorder), zero usage, insufficient data, reversal excluded from usage, threshold boundaries.
- ✅ **Done when:** the spec examples reproduce exactly and sparse data returns `insufficient_data`.

### Step 7 — Purchase orders *(~2.5 h)*
- `po_service`: create draft, edit, submit, receive (creates `purchase` ledger rows through `apply_movement` in the same DB transaction), cancel, status transitions with `INVALID_STATE` errors.
- `/recommendations/draft-pos` grouping by supplier.
- Wire incoming quantity into the reorder engine (open POs only).
- ✅ **Done when:** submitting a PO reduces the recommended reorder qty, and receiving it raises stock and closes the PO.

### Step 8 — Dashboard endpoints *(~1.5 h)*
- `/dashboard/summary`, `movement-chart`, `top-used`, `alerts`, `recent-transactions`, `category-value`.
- Health score formula (§6.7).
- ✅ **Done when:** numbers match what you get by manual SQL on the seed data.

### Step 9 — Reports & CSV *(~1.5 h)*
- `reporting_service` builds row lists once; router returns JSON or a streamed CSV depending on `format`.
- All five reports in §8.13 with date filters.
- ✅ **Done when:** CSV opens correctly in Excel (UTF-8 with BOM) and totals match the dashboard.

### Step 10 — Stocktake & insights *(~2.5 h, P1/P2)*
- `stocktake_service`: start, scan (uses the same `lookup` resolver), uncounted list, finalize → adjustments through `apply_movement`.
- `insight_service`: anomalies, dead stock, ABC, reconciliation.
- ✅ **Done when:** finalizing a stocktake with one wrong count produces exactly one adjustment and an audit log.

### Step 11 — CSV import & demo seed *(~2 h)*
- `/products/import` with `dry_run`.
- `seed_service` + `POST /dev/seed-demo`: ~25 realistic products (lab consumables, stationery, etc.), 30 days of usage with a few deliberate stories — one product about to run out, one with a usage spike (anomaly), one with an open PO, one dead-stock item, one with too little history.
- ✅ **Done when:** one click gives a dashboard that looks alive and every smart feature has something to show.

### Step 12 — Hardening & handoff *(~1.5 h)*
- Consistent error codes; validate all inputs (negative/zero quantity, SKU format, long strings).
- `/health`, README with run instructions, `.env.example`, Postman collection exported from `/openapi.json`.
- Run the full demo script from `features.md` end-to-end.
- ✅ **Done when:** a teammate can clone, run `docker compose up`, seed, and complete the demo without help.

**Rough total:** ~25 hours of backend work. If time is tight, cut in this order: Step 10 (insights/stocktake) → CSV import → ABC/dead stock → PO receive partials. **Never cut** Steps 4 and 6.

---

## 12. Security & reliability checklist

- [ ] Passwords hashed with bcrypt; hash never returned by any schema.
- [ ] `SECRET_KEY`, DB URL only from environment variables.
- [ ] CORS limited to the frontend origin.
- [ ] Every route has an explicit role dependency (add a test that fails if a route has none).
- [ ] Parameterised queries only (SQLAlchemy handles this).
- [ ] Stock changes only through `apply_movement`.
- [ ] No endpoint can UPDATE or DELETE a `stock_transactions` row.
- [ ] Dev/seed endpoints refuse to run unless `DEBUG=true`.
- [ ] CSV export escapes formula-injection characters (`=`, `+`, `-`, `@` at cell start).