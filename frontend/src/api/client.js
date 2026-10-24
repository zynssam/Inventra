// src/api/client.js — base fetch wrapper with JWT auth
export const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

function getToken() {
  try { return JSON.parse(sessionStorage.getItem("inventraUser"))?.token ?? null; }
  catch { return null; }
}

export class ApiError extends Error {
  constructor(status, code, message, field) {
    super(message);
    this.status = status; this.code = code; this.field = field;
  }
}

export async function apiFetch(path, opts = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(opts.headers ?? {}),
  };
  const res = await fetch(API_BASE + path, { ...opts, headers });

  if (res.status === 401) {
    sessionStorage.removeItem("inventraUser");
    window.location.href = "/login";
    throw new ApiError(401, "INVALID_CREDENTIALS", "Session expired");
  }

  const ct = res.headers.get("content-type") ?? "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError(res.status, body?.code ?? "ERROR", body?.detail ?? `HTTP ${res.status}`, body?.field);
  return body;
}

export const get  = (path, params) => apiFetch(path + (params ? "?" + new URLSearchParams(params) : ""));
export const post = (path, body)   => apiFetch(path, { method: "POST",  body: JSON.stringify(body) });
export const patch= (path, body)   => apiFetch(path, { method: "PATCH", body: JSON.stringify(body) });
export const put  = (path, body)   => apiFetch(path, { method: "PUT",   body: JSON.stringify(body) });
export const del  = (path)         => apiFetch(path, { method: "DELETE" });

export async function downloadCsv(path, filename) {
  const token = getToken();
  const res = await fetch(API_BASE + path, { headers: { Authorization: `Bearer ${token}` } });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
