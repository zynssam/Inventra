// src/pages/Audit.jsx
import { useEffect, useState, useCallback } from "react";
import { AuditLogs as API } from "../api";
import { PageHeader, Empty, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Search } from "lucide-react";

export default function Audit() {
  const toast = useToast();
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage]       = useState(1);
  const [total, setTotal]     = useState(0);
  const [filters, setFilters] = useState({ action: "", entity_type: "", date_from: "", date_to: "" });

  const fetchAll = useCallback(() => {
    setLoading(true);
    const params = { page, page_size: 25, ...Object.fromEntries(Object.entries(filters).filter(([,v]) => v)) };
    API.list(params)
      .then(d => { setItems(d.items ?? d); setTotal(d.total ?? d.length); })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [page, filters]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const setF = k => e => setFilters(f => ({ ...f, [k]: e.target.value }));

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Audit Log" subtitle={`${total} events recorded`} />

      <div className="toolbar">
        <div className="toolbar-left">
          <input className="input" placeholder="Action (e.g. create_product)" value={filters.action} onChange={setF("action")} style={{ minWidth: 200 }} />
          <input className="input" placeholder="Entity type" value={filters.entity_type} onChange={setF("entity_type")} style={{ minWidth: 140 }} />
          <input className="input" type="date" value={filters.date_from} onChange={setF("date_from")} />
          <input className="input" type="date" value={filters.date_to} onChange={setF("date_to")} />
          <button className="btn btn-secondary btn-sm" onClick={() => { setPage(1); fetchAll(); }}>
            <Search size={13} /> Filter
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>ID</th><th>Details</th></tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan="6"><Empty icon="🔍" message="No audit events found" /></td></tr>
              ) : items.map((a, i) => (
                <tr key={i}>
                  <td className="td-muted" style={{ whiteSpace: "nowrap" }}>{new Date(a.created_at).toLocaleString()}</td>
                  <td style={{ fontWeight: 600 }}>{a.user_name ?? a.user_id ?? "—"}</td>
                  <td><span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--purple)" }}>{a.action}</span></td>
                  <td className="td-muted">{a.entity_type ?? "—"}</td>
                  <td className="td-muted font-mono">{a.entity_id ?? "—"}</td>
                  <td className="td-muted" style={{ maxWidth: 260, whiteSpace: "normal", fontSize: 11 }}>
                    {a.details ? (typeof a.details === "object" ? JSON.stringify(a.details).slice(0, 80) : String(a.details).slice(0, 80)) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {total > 25 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button className="btn btn-secondary btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ lineHeight: "32px", fontSize: 12, color: "var(--muted)" }}>Page {page}</span>
          <button className="btn btn-secondary btn-sm" disabled={items.length < 25} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}
    </div>
  );
}
