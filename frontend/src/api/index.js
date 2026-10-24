// src/api/index.js — all domain API modules
import { get, post, patch, put, del, downloadCsv } from "./client";

export const Auth = {
  login:          (email, password) => post("/auth/login", { email, password }),
  me:             ()                => get("/auth/me"),
  changePassword: (current, next)   => post("/auth/change-password", { current_password: current, new_password: next }),
};

export const Dashboard = {
  summary:            ()           => get("/dashboard/summary"),
  alerts:             ()           => get("/dashboard/alerts"),
  movementChart:      (days = 30)  => get("/dashboard/movement-chart", { days }),
  topUsed:            (days = 30)  => get("/dashboard/top-used", { days, limit: 5 }),
  categoryValue:      ()           => get("/dashboard/category-value"),
  recentTransactions: (limit = 10) => get("/dashboard/recent-transactions", { limit }),
};

export const Products = {
  list:    (p = {}) => get("/products", p),
  get:     (id)     => get(`/products/${id}`),
  create:  (b)      => post("/products", b),
  update:  (id, b)  => patch(`/products/${id}`, b),
  archive: (id)     => del(`/products/${id}`),
};

export const Transactions = {
  list:       (p = {}) => get("/transactions", p),
  stockIn:    (b)      => post("/transactions/stock-in", b),
  stockOut:   (b)      => post("/transactions/stock-out", b),
  adjustment: (b)      => post("/transactions/adjustments", b),
  reverse:    (id, r)  => post(`/transactions/${id}/reverse`, { reason: r }),
};

export const Forecasts = {
  list: (p = {}) => get("/forecasts", p),
  get:  (id, p)  => get(`/forecasts/${id}`, p),
};

export const Recommendations = {
  list:     (p = {}) => get("/recommendations", p),
  get:      (id, p)  => get(`/recommendations/${id}`, p),
  simulate: (b)      => post("/recommendations/simulate", b),
};

export const Categories = {
  list:   ()       => get("/categories"),
  create: (b)      => post("/categories", b),
  update: (id, b)  => patch(`/categories/${id}`, b),
  delete: (id)     => del(`/categories/${id}`),
};

export const Suppliers = {
  list:   (p = {}) => get("/suppliers", p),
  get:    (id)     => get(`/suppliers/${id}`),
  create: (b)      => post("/suppliers", b),
  update: (id, b)  => patch(`/suppliers/${id}`, b),
  delete: (id)     => del(`/suppliers/${id}`),
};

export const Reports = {
  stockMovements:      (p = {}) => get("/reports/stock-movements", p),
  inventoryValuation:  ()       => get("/reports/inventory-valuation"),
  stockStatus:         ()       => get("/reports/stock-status"),
  downloadMovements:   (p)      => downloadCsv("/reports/stock-movements?" + new URLSearchParams({ ...p, format: "csv" }), "stock-movements.csv"),
  downloadValuation:   ()       => downloadCsv("/reports/inventory-valuation?format=csv", "inventory-valuation.csv"),
  downloadStatus:      ()       => downloadCsv("/reports/stock-status?format=csv", "stock-status.csv"),
};

export const AuditLogs = {
  list: (p = {}) => get("/audit-logs", p),
};

export const Settings = {
  get:    ()  => get("/settings"),
  update: (b) => put("/settings", b),
};

export const Users = {
  list:   (p = {}) => get("/users", p),
  get:    (id)     => get(`/users/${id}`),
  create: (b)      => post("/users", b),
  update: (id, b)  => patch(`/users/${id}`, b),
  delete: (id)     => del(`/users/${id}`),
};

export const Meta = { enums: () => get("/meta/enums") };
export const Health = { check: () => get("/health") };
