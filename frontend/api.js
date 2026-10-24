/**
 * api.js — Inventra frontend API layer
 * All calls to the FastAPI backend go through this file.
 *
 * Backend base URL — change this if the server moves.
 */
const API_BASE = "http://localhost:8000/api/v1";
const SESSION_KEY = "inventraUser"; // { token, user_id, role, full_name, email }

// ─── Auth helpers ────────────────────────────────────────────────────────────

function getSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch { return null; }
}

function setSession(data) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
}

function getToken() {
  return getSession()?.token ?? null;
}

function authHeaders() {
  const token = getToken();
  return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

/**
 * @param {string} path   e.g. "/auth/login"
 * @param {object} opts   fetch options override
 * @returns {Promise<any>}
 */
async function api(path, opts = {}) {
  const url = API_BASE + path;
  const defaults = { headers: authHeaders() };
  const merged = { ...defaults, ...opts, headers: { ...defaults.headers, ...(opts.headers || {}) } };

  const res = await fetch(url, merged);

  if (res.status === 401) {
    clearSession();
    if (!window.location.pathname.endsWith("login.html")) {
      window.location.href = "login.html";
    }
    throw new ApiError(401, "INVALID_CREDENTIALS", "Session expired — please sign in again.");
  }

  let body;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    body = await res.json();
  } else {
    body = await res.text();
  }

  if (!res.ok) {
    const msg = body?.detail ?? `HTTP ${res.status}`;
    const code = body?.code ?? "ERROR";
    throw new ApiError(res.status, code, msg, body?.field);
  }
  return body;
}

class ApiError extends Error {
  constructor(status, code, message, field) {
    super(message);
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

const Auth = {
  async login(email, password) {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    // data: { access_token, token_type, user_id, role, full_name }
    setSession({
      token: data.access_token,
      user_id: data.user_id,
      role: data.role,
      full_name: data.full_name,
      email,
    });
    return data;
  },

  async me() {
    return api("/auth/me");
  },

  async changePassword(currentPassword, newPassword) {
    return api("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  logout() {
    clearSession();
    window.location.href = "login.html";
  },
};

// ─── Dashboard ────────────────────────────────────────────────────────────────

const Dashboard = {
  summary: () => api("/dashboard/summary"),
  alerts: () => api("/dashboard/alerts"),
  movementChart: (days = 30) => api(`/dashboard/movement-chart?days=${days}`),
  topUsed: (days = 30, limit = 5) => api(`/dashboard/top-used?days=${days}&limit=${limit}`),
  categoryValue: () => api("/dashboard/category-value"),
  recentTransactions: (limit = 10) => api(`/dashboard/recent-transactions?limit=${limit}`),
};

// ─── Products ─────────────────────────────────────────────────────────────────

const Products = {
  list: (params = {}) => api("/products?" + new URLSearchParams(params)),
  get: (id) => api(`/products/${id}`),
  create: (body) => api("/products", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => api(`/products/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  archive: (id) => api(`/products/${id}`, { method: "DELETE" }),
};

// ─── Transactions ─────────────────────────────────────────────────────────────

const Transactions = {
  list: (params = {}) => api("/transactions?" + new URLSearchParams(params)),
  stockIn: (body) => api("/transactions/stock-in", { method: "POST", body: JSON.stringify(body) }),
  stockOut: (body) => api("/transactions/stock-out", { method: "POST", body: JSON.stringify(body) }),
  adjustment: (body) => api("/transactions/adjustments", { method: "POST", body: JSON.stringify(body) }),
  reverse: (id, reason) => api(`/transactions/${id}/reverse`, { method: "POST", body: JSON.stringify({ reason }) }),
};

// ─── Forecasts ────────────────────────────────────────────────────────────────

const Forecasts = {
  list: (params = {}) => api("/forecasts?" + new URLSearchParams(params)),
  get: (id, params = {}) => api(`/forecasts/${id}?` + new URLSearchParams(params)),
};

// ─── Recommendations ──────────────────────────────────────────────────────────

const Recommendations = {
  list: (params = {}) => api("/recommendations?" + new URLSearchParams(params)),
  get: (id, params = {}) => api(`/recommendations/${id}?` + new URLSearchParams(params)),
  simulate: (body) => api("/recommendations/simulate", { method: "POST", body: JSON.stringify(body) }),
};

// ─── Categories ───────────────────────────────────────────────────────────────

const Categories = {
  list: () => api("/categories"),
  create: (body) => api("/categories", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => api(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (id) => api(`/categories/${id}`, { method: "DELETE" }),
};

// ─── Suppliers ────────────────────────────────────────────────────────────────

const Suppliers = {
  list: (params = {}) => api("/suppliers?" + new URLSearchParams(params)),
  get: (id) => api(`/suppliers/${id}`),
  create: (body) => api("/suppliers", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => api(`/suppliers/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (id) => api(`/suppliers/${id}`, { method: "DELETE" }),
};

// ─── Reports ──────────────────────────────────────────────────────────────────

const Reports = {
  stockMovements: (params = {}) => api("/reports/stock-movements?" + new URLSearchParams(params)),
  inventoryValuation: () => api("/reports/inventory-valuation"),
  stockStatus: () => api("/reports/stock-status"),

  downloadCsv(path, filename) {
    const token = getToken();
    const url = `${API_BASE}${path}&format=csv`;
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    // Add token via URL is not ideal; use a hidden form instead for auth
    fetch(url, { headers: authHeaders() })
      .then(r => r.blob())
      .then(blob => {
        const objectUrl = URL.createObjectURL(blob);
        a.href = objectUrl;
        a.click();
        URL.revokeObjectURL(objectUrl);
      });
  },
};

// ─── Audit Logs ───────────────────────────────────────────────────────────────

const AuditLogs = {
  list: (params = {}) => api("/audit-logs?" + new URLSearchParams(params)),
};

// ─── Settings ─────────────────────────────────────────────────────────────────

const Settings = {
  get: () => api("/settings"),
  update: (body) => api("/settings", { method: "PUT", body: JSON.stringify(body) }),
};

// ─── Users ────────────────────────────────────────────────────────────────────

const Users = {
  list: (params = {}) => api("/users?" + new URLSearchParams(params)),
  get: (id) => api(`/users/${id}`),
  create: (body) => api("/users", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => api(`/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (id) => api(`/users/${id}`, { method: "DELETE" }),
};

// ─── Meta ─────────────────────────────────────────────────────────────────────

const Meta = {
  enums: () => api("/meta/enums"),
};

// ─── Health ───────────────────────────────────────────────────────────────────

const Health = {
  check: () => api("/health"),
};

// ─── Utility helpers ──────────────────────────────────────────────────────────

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function stateClass(state) {
  const map = {
    healthy: "healthy", ok: "healthy",
    low_stock: "warning", warning: "warning",
    out_of_stock: "critical", critical: "critical",
    insufficient_data: "muted", no_recent_usage: "muted",
  };
  return map[state] ?? "muted";
}

function stateLabel(state) {
  return (state ?? "").replace(/_/g, " ");
}

function roleLabel(role) {
  const map = { admin: "Admin", store_manager: "Store Manager", viewer: "Viewer" };
  return map[role] ?? role;
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

function canWrite() {
  const session = getSession();
  return session?.role === "admin" || session?.role === "store_manager";
}

function isAdmin() {
  return getSession()?.role === "admin";
}
