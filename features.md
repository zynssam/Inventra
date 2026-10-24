Inventra# StockSense — Features

> Track Smarter. Restock Earlier. Never Run Out.

**Goal:** a simple, working prototype that contains *all* the features from the original plan, plus a few additions that make it stand out. This file lists what is built, in what priority, how to know it works, and what is intentionally left out. Technical details and the full API are in `architecture.md`.

---

## 1. Review of the original plan

The plan is solid: the three-layer stack, atomic stock updates, rules-based forecasting, and "backend enforces permissions" are all the right calls. These are the gaps and fixes worth making before you build.

### Things that need fixing

| # | Issue in the original | Fix |
|---|---|---|
| 1 | "Delete product" conflicts with "never delete history" (transactions reference products). | **Archive** products instead of deleting. Hard delete only if no transactions exist. |
| 2 | `stock_transactions` has `quantity` + `type`, so every query must know which types are negative. | Store a **signed `quantity_delta`** plus `balance_after` on each row. Simpler queries, and a built-in audit trail. |
| 3 | "Average daily usage" is not defined precisely. Dividing by days-with-activity overstates usage. | Divide total usage by the **whole window** (or product age if newer). See `architecture.md` §6.2. |
| 4 | Returns and adjustments could be mistaken for usage. | Only `sale`, `issue`, `consumption` count as usage; reversals cancel them. |
| 5 | `current_quantity` can drift from the ledger over time. | Add a **reconciliation check** (`/insights/reconciliation`) and a DB `CHECK (current_quantity >= 0)`. |
| 6 | Double-clicks or flaky mobile networks can submit the same movement twice. | Optional `client_request_id` makes POSTs **idempotent**. |
| 7 | Forecasting can't be demoed with an empty database. | A **demo seed endpoint** that generates 30 days of history on demand. This matters more than any other item for a live demo. |
| 8 | No endpoint receives a purchase order into stock, so "incoming stock" can never resolve. | PO lifecycle: `draft → ordered → partially_received → received`; receiving creates stock-in rows atomically. |
| 9 | Lead time and safety stock are left as "later". | They cost two columns. Add them now with default 0, so the formula equals the original until used. |
| 10 | "Viewer: reports only" but no one defined who can **export**. | Everyone can export CSV; only admin touches users/settings/audit. |
| 11 | Quantities are assumed whole numbers. | Fine for the prototype; note it. Use decimals later for litres/kg. |
| 12 | Archived or low-sample products can produce misleading forecasts. | Forecast has explicit states: `critical`, `warning`, `ok`, `insufficient_data`, `no_recent_usage`, `out_of_stock`. |

### Wording to avoid in the demo
- Don't say "AI" or "machine learning". Say **"transparent, rule-based inventory intelligence"**. Judges respect honesty, and it matches your own design principle.
- Don't say forecasts are "accurate". Say they are **estimates from recent usage**, with the numbers shown.

---

## 2. Feature list with priorities

**P0 = must work for the demo · P1 = full-feature prototype · P2 = polish / differentiators**

### A. Core

| ID | Feature | Pri | Acceptance criteria |
|---|---|:-:|---|
| C1 | **Login & JWT auth** | P0 | Wrong password → clear error. Token expires after 8 h. Logout clears token. |
| C2 | **Role-based access** (Admin / Storekeeper / Viewer) | P0 | Viewer cannot see "Add" buttons **and** gets `403` if they call the API directly. |
| C3 | **Dashboard** KPIs: total products, total units, low-stock, out-of-stock, inventory value | P0 | Numbers match the Products table. |
| C4 | Dashboard charts: movement (in vs out, 30 d), top-used, value by category | P1 | Hover shows exact values; empty state when no data. |
| C5 | Dashboard alerts & recent transactions | P0 | Alert list sorted by severity; click opens the product. |
| C6 | **Product CRUD** (name, unique SKU, category, unit, cost, optional price, min stock) | P0 | Duplicate SKU rejected with a field-level message. |
| C7 | Product search, sort, filter (category, supplier, status), pagination | P0 | Searches name and SKU; filters combine. |
| C8 | Product detail page (info, status, history, usage chart, QR, forecast, recommendation) | P0 | One screen answers "what is this, how much, how fast is it going, what to do". |
| C9 | **Stock in** (purchase, return) | P0 | Quantity updates immediately; ledger row shows user, time, reason, supplier. |
| C10 | **Stock out** (sale, lab issue, consumption) with recipient | P0 | Over-issuing blocked with "Only N available". |
| C11 | **Adjustments** (admin, reason required) | P1 | Appears in history as `adjustment` with before/after balance. |
| C12 | **Reversal** of a transaction (admin) | P1 | Can only be reversed once; original stays visible, marked "reversed". |
| C13 | Full transaction history with filters (product, type, user, date) | P0 | Sortable, paginated, exportable. |
| C14 | **Categories & suppliers** CRUD; supplier detail shows products and purchase history | P1 | Can't delete a category that still has products. |
| C15 | **User management** (admin) | P1 | Create users, change role, deactivate. |
| C16 | **Settings** (target days, window, warning/critical thresholds) | P1 | Changing a threshold immediately changes forecast states. |

### B. Smart features

| ID | Feature | Pri | Acceptance criteria |
|---|---|:-:|---|
| S1 | **Stock forecasting**: average daily usage, days until stockout, projected date | P0 | Example: 24 in stock ÷ 4/day = 6 days. |
| S2 | Forecast states with colour (critical / warning / ok) | P0 | Thresholds come from settings. |
| S3 | **"Insufficient data"** handling | P0 | Fewer than 3 days of usage → shows "Insufficient data", no number. |
| S4 | **Smart reorder suggestions** with the written reason | P0 | Example: usage 5/day, 20 days, stock 12, incoming 10 → **78**. Reason text lists every input. |
| S5 | Incoming stock from open purchase orders | P1 | Submitting a PO lowers the suggestion; draft POs don't count. |
| S6 | Lead time + safety stock (optional per product) | P1 | Defaults 0 → same result as the base formula. |
| S7 | **QR code generation** per product (payload `SS:{sku}`, never the quantity) | P0 | QR can be shown, downloaded as PNG, printed. |
| S8 | **QR scanning** via camera → opens product → start stock in/out | P0 | Works on a phone browser over HTTPS/localhost. |
| S9 | Manual SKU search fallback | P0 | Shown whenever camera permission is denied or unavailable. |
| S10 | **Reports**: movements, valuation, stock status, restock plan, supplier purchases | P1 | Date filters; totals agree with the dashboard. |
| S11 | **CSV export** for every report | P0 | Opens in Excel with correct columns; no formula-injection. |
| S12 | **Audit trail** (admin view): who, what, when, before/after | P1 | Every create/update/stock action is logged. |
| S13 | Purchase orders: create, submit, receive (partial too), cancel | P1 | Receiving increases stock through the same atomic path as stock-in. |

### C. Differentiators (what makes it unique)

These are cheap to build because they reuse the same usage query and ledger.

| ID | Feature | Pri | Why it stands out |
|---|---|:-:|---|
| D1 | **"Explain this" panel** on every forecast and recommendation: inputs, formula, confidence (high/medium/low) | P0 | Trust. Most demos show a number; yours shows the reasoning. |
| D2 | **One-click draft purchase orders** from the restock list, grouped by supplier | P1 | Closes the loop: *detect → recommend → act*. |
| D3 | **What-if simulator**: slide "target days" and "window" and see total reorder quantity and cost update live | P1 | Visual and interactive; nothing is saved. |
| D4 | **QR stocktake mode**: scan shelf items, enter counts, see variances and uncounted items, finalize into adjustments | P1 | Turns the QR feature from "lookup" into a real warehouse workflow. |
| D5 | **Continuous scan mode**: scan, enter quantity, next, without leaving the camera screen | P2 | Fast, feels like a real scanner app. |
| D6 | **Anomaly flags**: unusual spike in usage or a suspiciously large single issue (z-score, shown with numbers) | P2 | Catches typos like 500 instead of 5, and pilferage. |
| D7 | **Dead-stock & ABC analysis** | P2 | Shows where money is tied up and what matters most. |
| D8 | **Inventory health score** (0–100) with the formula in a tooltip | P2 | A single number that fits on a slide. |
| D9 | **Recipient/department tracking** for lab issues, with "usage by department" in reports | P2 | Fits labs and campus stores specifically, which is your target audience. |
| D10 | **Reconciliation check**: ledger vs cached quantity | P2 | Strong integrity story: "we can prove the numbers add up". |
| D11 | **Bulk QR label sheet** (print-ready page of QR codes + name + SKU) | P2 | Practical: lets a lab tag its shelves in minutes. |
| D12 | **CSV product import** with dry-run validation | P2 | Gets a real inventory in without typing it. |
| D13 | **Demo seed with built-in "stories"** (one item about to run out, one spiking, one with a PO on the way, one dead, one with too little data) | P0 | The live demo never hits an empty screen. |

> **Positioning line:** *"StockSense doesn't just record stock. It tells you what's running out, how soon, how much to order, and why. And you can verify every number."*

---

## 3. What the prototype intentionally does NOT do

- No machine-learning forecasting, seasonality, or demand prediction models.
- No multi-warehouse / multi-location transfers (a free-text `location` field only).
- No batch/lot or expiry tracking (the natural next step for chemicals).
- No email / SMS notifications (alerts live in the app).
- No barcode hardware integration (camera scanning only).
- No multi-currency, taxes, or invoicing.
- No refresh tokens, SSO, or password-reset email.
- No offline mode.

Mention these as the **roadmap** in your pitch, with batch/expiry and notifications first.

---

## 4. Screens

| # | Screen | Main things on it |
|---|---|---|
| 1 | Login | Email/password, error states |
| 2 | Dashboard | 5 KPI cards, health score, movement chart, alerts, recent transactions, quick actions (Stock in/out, Scan) |
| 3 | Products | Table with search/filter/sort, status chips, forecast chip ("6 days left"), Add/Import |
| 4 | Product detail | Info, QR, usage chart, forecast + "Explain", recommendation + "Draft PO", history, stock in/out buttons |
| 5 | Stock movements | Tabs: Stock in · Stock out · Adjustment · History |
| 6 | Scan | Camera view + SKU fallback → product card with Stock in/out; toggle continuous mode |
| 7 | Stocktake | Session list; counting screen with scanned items, variance, uncounted list, finalize |
| 8 | Restocking | Table of suggestions with reasons, what-if sliders, select rows → Create draft POs |
| 9 | Purchase orders | List, detail, receive form |
| 10 | Suppliers & categories | Lists, supplier detail with history |
| 11 | Reports | Report picker, date filters, preview, CSV download |
| 12 | Insights | Anomalies, dead stock, ABC |
| 13 | Users & settings | Users table, thresholds, audit log, "Load demo data" |

**Status chip colours:** Healthy = green · Low = amber · Out of stock = red · Forecast critical = red · warning = amber · ok = green · insufficient data = grey.

**UX rules:** loading skeletons, empty states with a call to action, confirmation dialogs for adjust/reverse/archive, inline validation, toast on success, mobile-friendly Scan and Stock in/out screens.

---

## 5. Demo script (about 5 minutes)

Run `POST /dev/seed-demo` (button in Settings) before you start.

1. **Dashboard.** "At a glance: what we have, what's running out, what changed." Point at the alert list and the health score.
2. **Add a product** "Demo Beaker 250ml" with a new SKU and an opening quantity of 20. Show it appear in the table.
3. **Record a purchase** of 30. The quantity goes 20 → 50 and the ledger row shows user, time and reason.
4. **Print/show the QR**, then **scan it with a phone**. The product page opens. (Fallback: type the SKU.)
5. **Issue 8 units** to "Chemistry Lab". Quantity drops to 42. **Try issuing 500**: show the "only 42 available" block.
6. **Open an at-risk seeded product.** Show "6 days left", click **Explain**: usage, formula, confidence.
7. **Restocking page.** Show the suggested quantity with its reason. Drag the **what-if** slider from 20 to 30 days and watch the totals change.
8. **Create draft PO** from the selected items. Submit it and show the suggestion shrink because stock is now incoming. Receive it and watch stock rise.
9. **Stocktake (30 s).** Scan two shelf items, enter a wrong count, finalize, and show the adjustment in history and the audit log.
10. **Reports.** Export the movements report to CSV and open it.
11. **Login as Viewer.** Buttons vanish, and a direct API call returns `403`.

Close with: *"Every number you saw is backed by an append-only ledger. Here's the reconciliation check showing zero mismatches."*

---

## 6. Definition of done for the prototype

- [ ] Demo script runs end-to-end with no manual DB edits.
- [ ] Spec examples reproduce exactly (6 days; 78 units).
- [ ] No way to make stock negative, via UI or API.
- [ ] Viewer and Storekeeper restrictions verified via direct API calls.
- [ ] Every stock change appears in history and the audit log.
- [ ] Reconciliation shows zero mismatches after the demo.
- [ ] Works on a phone for Scan and Stock in/out.
- [ ] `docker compose up` + seed gets a fresh machine to demo state.
- [ ] README lists logins, run steps, and the roadmap.