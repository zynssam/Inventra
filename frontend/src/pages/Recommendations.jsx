// src/pages/Recommendations.jsx
import { useEffect, useState, useCallback } from "react";
import { Recommendations as API } from "../api";
import { PageHeader, ForecastBadge, Badge, Empty, Modal, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { ShoppingCart, Info } from "lucide-react";

const CONFIDENCE_COLOR = { high: "#4ade80", medium: "#fbbf24", low: "#8890a8" };

function SimulateModal({ onClose }) {
  const [form, setForm] = useState({ target_days: 30, window_days: 30, lead_time_days: 7, safety_days: 3 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = k => e => setForm(f => ({ ...f, [k]: Number(e.target.value) }));

  async function run() {
    setError(""); setLoading(true);
    try { setResult(await API.simulate(form)); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  const fmtCurrency = v => `$${Number(v).toFixed(2)}`;

  return (
    <Modal title="What-If Simulation" subtitle="Simulate reorder quantities under different assumptions." onClose={onClose} wide>
      {error && <div className="error-msg">{error}</div>}
      <div className="input-row">
        <div className="field"><label>Target Days</label><input className="input" type="number" value={form.target_days} onChange={set("target_days")} /></div>
        <div className="field"><label>Window Days</label><input className="input" type="number" value={form.window_days} onChange={set("window_days")} /></div>
      </div>
      <div className="input-row">
        <div className="field"><label>Lead Time Days</label><input className="input" type="number" value={form.lead_time_days} onChange={set("lead_time_days")} /></div>
        <div className="field"><label>Safety Days</label><input className="input" type="number" value={form.safety_days} onChange={set("safety_days")} /></div>
      </div>
      <button className="btn btn-primary" onClick={run} disabled={loading} style={{ marginBottom: 16 }}>
        {loading ? "Simulating…" : "Run Simulation"}
      </button>
      {result && (
        <div>
          <div style={{ marginBottom: 10, fontWeight: 700 }}>
            Total Estimated Cost: <span style={{ color: "var(--purple)" }}>{fmtCurrency(result.total_estimated_cost ?? 0)}</span>
          </div>
          <div className="table-wrap" style={{ maxHeight: 300, overflowY: "auto" }}>
            <table>
              <thead><tr><th>Product</th><th>Reorder Qty</th><th>Est. Cost</th><th>Confidence</th></tr></thead>
              <tbody>
                {(result.items ?? []).filter(i => i.reorder_qty > 0).map(i => (
                  <tr key={i.product_id}>
                    <td>{i.product_name}</td>
                    <td className="quantity">{i.reorder_qty}</td>
                    <td>{fmtCurrency(i.estimated_cost)}</td>
                    <td><Badge state={i.confidence} label={i.confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Close</button>
      </div>
    </Modal>
  );
}

export default function Recommendations() {
  const toast = useToast();
  const [items, setItems]       = useState([]);
  const [total, setTotal]       = useState(0);
  const [loading, setLoading]   = useState(true);
  const [targetDays, setTargetDays] = useState(30);
  const [includeAll, setIncludeAll] = useState(false);
  const [simulate, setSimulate] = useState(false);

  const fetch = useCallback(() => {
    setLoading(true);
    API.list({ target_days: targetDays, include_all: includeAll })
      .then(d => { setItems(d.items ?? d); setTotal(d.total_estimated_cost ?? 0); })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [targetDays, includeAll]);

  useEffect(() => { fetch(); }, [fetch]);

  const fmtCurrency = v => `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Reorder Recommendations" subtitle="AI-powered restocking suggestions based on usage forecasts">
        <button className="btn btn-secondary" onClick={() => setSimulate(true)}><Info size={14} /> Simulate</button>
      </PageHeader>

      {/* Total cost banner */}
      {total > 0 && (
        <div className="card" style={{ marginBottom: 16, background: "var(--purple-glow)", borderColor: "var(--purple)", display: "flex", alignItems: "center", gap: 14 }}>
          <ShoppingCart size={20} color="var(--purple)" />
          <div>
            <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Total Estimated Cost</div>
            <div style={{ font: "700 22px Manrope", color: "var(--purple)" }}>{fmtCurrency(total)}</div>
          </div>
        </div>
      )}

      <div className="toolbar">
        <div className="toolbar-left">
          <div className="field" style={{ margin: 0 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", marginRight: 8 }}>Target Days:</label>
            <select className="input" style={{ width: "auto" }} value={targetDays} onChange={e => setTargetDays(Number(e.target.value))}>
              {[7,14,30,60,90].map(d => <option key={d} value={d}>{d} days</option>)}
            </select>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-2)", cursor: "pointer" }}>
            <input type="checkbox" checked={includeAll} onChange={e => setIncludeAll(e.target.checked)} />
            Show all products
          </label>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Product</th><th>Forecast</th><th>Confidence</th><th>Reorder Qty</th><th>Est. Cost</th><th>Avg Daily</th><th>Explanation</th></tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan="7"><Empty icon="✅" message="No reorders needed right now" /></td></tr>
              ) : items.map(r => (
                <tr key={r.product_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{r.product_name}</div>
                    <div className="td-muted font-mono">{r.sku}</div>
                  </td>
                  <td><ForecastBadge state={r.forecast_state} /></td>
                  <td>
                    <span style={{ fontWeight: 700, color: CONFIDENCE_COLOR[r.confidence] ?? "var(--muted)", fontSize: 12 }}>
                      {r.confidence ?? "—"}
                    </span>
                  </td>
                  <td><span className="quantity" style={{ color: r.reorder_qty > 0 ? "var(--purple)" : "var(--muted)" }}>{r.reorder_qty}</span></td>
                  <td style={{ fontWeight: 600 }}>{r.reorder_qty > 0 ? fmtCurrency(r.estimated_cost) : "—"}</td>
                  <td className="td-muted">{Number(r.inputs?.avg_daily_usage ?? 0).toFixed(2)}/day</td>
                  <td className="td-muted" style={{ maxWidth: 220, whiteSpace: "normal", fontSize: 11 }}>{r.explanation ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {simulate && <SimulateModal onClose={() => setSimulate(false)} />}
    </div>
  );
}
