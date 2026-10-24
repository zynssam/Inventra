// src/components/ui.jsx — shared UI primitives
import { X } from "lucide-react";
import { useEffect, useRef } from "react";

// ── Badge ────────────────────────────────────────────────────────────────────
export function Badge({ state, label }) {
  const cls = state ?? "muted";
  const text = label ?? (state ?? "").replace(/_/g, " ");
  return <span className={`badge badge-${cls}`}>{text}</span>;
}

export function StatusBadge({ status }) {
  const map = { healthy: "Healthy", low_stock: "Low Stock", out_of_stock: "Out of Stock" };
  return <Badge state={status} label={map[status] ?? status} />;
}

export function RoleBadge({ role }) {
  const map = { admin: "Admin", store_manager: "Store Manager", viewer: "Viewer" };
  return <Badge state={role} label={map[role] ?? role} />;
}

export function ForecastBadge({ state }) {
  const map = { ok: "OK", warning: "Warning", critical: "Critical", out_of_stock: "Out of Stock", insufficient_data: "No Data", no_recent_usage: "No Usage" };
  return <Badge state={state} label={map[state] ?? state} />;
}

// ── Modal ────────────────────────────────────────────────────────────────────
export function Modal({ title, subtitle, onClose, children, wide }) {
  const overlayRef = useRef();
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="modal-overlay" ref={overlayRef} onClick={e => e.target === overlayRef.current && onClose()}>
      <div className={`modal${wide ? " modal-wide" : ""}`}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: subtitle ? 4 : 20 }}>
          <h2 className="modal-title">{title}</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><X size={16} /></button>
        </div>
        {subtitle && <p className="modal-sub">{subtitle}</p>}
        {children}
      </div>
    </div>
  );
}

// ── Toast ────────────────────────────────────────────────────────────────────
export function ToastContainer({ toasts, remove }) {
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span style={{ flex: 1 }}>{t.message}</span>
          <button className="btn btn-ghost btn-icon" style={{ padding: 4 }} onClick={() => remove(t.id)}>
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Spinner / Loading ─────────────────────────────────────────────────────────
export function Spinner() { return <div className="spinner" />; }
export function LoadingCenter() {
  return <div className="loading-center"><Spinner /></div>;
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function Empty({ icon = "📦", message = "Nothing here yet." }) {
  return <div className="empty"><div className="empty-icon">{icon}</div><p>{message}</p></div>;
}

// ── Confirm Dialog ────────────────────────────────────────────────────────────
export function Confirm({ title, message, onConfirm, onClose, danger }) {
  return (
    <Modal title={title} onClose={onClose}>
      <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 22 }}>{message}</p>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} onClick={() => { onConfirm(); onClose(); }}>
          {danger ? "Delete" : "Confirm"}
        </button>
      </div>
    </Modal>
  );
}

// ── Page Header ───────────────────────────────────────────────────────────────
export function PageHeader({ eyebrow, title, subtitle, children }) {
  return (
    <div className="page-header" style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12 }}>
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 style={{ font: "700 22px Manrope", letterSpacing: -0.5 }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{subtitle}</p>}
      </div>
      {children && <div style={{ display: "flex", gap: 10 }}>{children}</div>}
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
export function StatCard({ label, value, sub, icon, color = "var(--purple)" }) {
  return (
    <div className="stat-card">
      {icon && <div className="stat-icon" style={{ background: color + "20", color }}>{icon}</div>}
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value ?? "—"}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
