// src/pages/Reports.jsx
import { useState } from "react";
import { Reports as API } from "../api";
import { PageHeader, LoadingCenter, Empty, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Download, FileText, BarChart2, Package } from "lucide-react";

const fmtCurrency = v => `$${Number(v ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
const fmtDate = iso => iso ? new Date(iso).toLocaleDateString() : "—";

function ReportTab({ active, onClick, icon: Icon, label }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 8, padding: "10px 18px",
      borderRadius: "var(--radius-sm)", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
      background: active ? "var(--purple-glow)" : "transparent",
      color: active ? "var(--purple)" : "var(--text-2)",
      transition: "all 0.15s",
    }}>
      <Icon size={15} />{label}
    </button>
  );
}

export default function Reports() {
  const toast = useToast();
  const [tab, setTab]       = useState("movements");
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ date_from: "", date_to: "", txn_type: "" });

  async function fetchReport() {
    setLoading(true); setData(null);
    try {
      const result =
        tab === "movements"  ? await API.stockMovements(Object.fromEntries(Object.entries(filters).filter(([,v]) => v))) :
        tab === "valuation"  ? await API.inventoryValuation() :
        await API.stockStatus();
      setData(result);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }

  function handleDownload() {
    if (tab === "movements")  API.downloadMovements(filters);
    if (tab === "valuation")  API.downloadValuation();
    if (tab === "status")     API.downloadStatus();
  }

  const setF = k => e => setFilters(f => ({ ...f, [k]: e.target.value }));

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Reports" subtitle="Generate and export inventory reports">
        <button className="btn btn-secondary" onClick={handleDownload}><Download size={14} /> Export CSV</button>
      </PageHeader>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, background: "var(--surface-2)", borderRadius: "var(--radius)", padding: 6, marginBottom: 20, border: "1px solid var(--line)", width: "fit-content" }}>
        <ReportTab active={tab === "movements"} onClick={() => { setTab("movements"); setData(null); }} icon={BarChart2} label="Stock Movements" />
        <ReportTab active={tab === "valuation"} onClick={() => { setTab("valuation"); setData(null); }} icon={FileText} label="Inventory Valuation" />
        <ReportTab active={tab === "status"}    onClick={() => { setTab("status"); setData(null); }}    icon={Package} label="Stock Status" />
      </div>

      {/* Filters for movements */}
      {tab === "movements" && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div className="field" style={{ margin: 0 }}>
              <label>From</label>
              <input className="input" type="date" value={filters.date_from} onChange={setF("date_from")} />
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label>To</label>
              <input className="input" type="date" value={filters.date_to} onChange={setF("date_to")} />
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label>Type</label>
              <select className="input" value={filters.txn_type} onChange={setF("txn_type")}>
                <option value="">All Types</option>
                {["stock_in","stock_out","adjustment","reversal","po_receipt","stocktake"].map(t =>
                  <option key={t} value={t}>{t.replace("_", " ")}</option>
                )}
              </select>
            </div>
            <button className="btn btn-primary" onClick={fetchReport}>Generate Report</button>
          </div>
        </div>
      )}

      {tab !== "movements" && (
        <div style={{ marginBottom: 16 }}>
          <button className="btn btn-primary" onClick={fetchReport}>Generate Report</button>
        </div>
      )}

      {/* Results */}
      {loading && <LoadingCenter />}

      {data && tab === "movements" && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Product</th><th>Type</th><th>Qty Δ</th><th>Balance After</th><th>Reason</th></tr></thead>
              <tbody>
                {(data.items ?? data).length === 0
                  ? <tr><td colSpan="6"><Empty message="No movements in this period" /></td></tr>
                  : (data.items ?? data).map((r, i) => (
                    <tr key={i}>
                      <td className="td-muted">{fmtDate(r.created_at)}</td>
                      <td>{r.product_name ?? r.product_id}</td>
                      <td><span style={{ fontSize: 11, fontWeight: 600, color: r.quantity_delta >= 0 ? "#4ade80" : "#f87171" }}>{r.txn_type?.replace("_"," ")}</span></td>
                      <td className="quantity" style={{ color: r.quantity_delta >= 0 ? "#4ade80" : "#f87171" }}>{r.quantity_delta >= 0 ? "+" : ""}{r.quantity_delta}</td>
                      <td>{r.balance_after}</td>
                      <td className="td-muted">{r.reason ?? "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data && tab === "valuation" && (
        <>
          <div className="card" style={{ marginBottom: 12, display: "flex", gap: 24 }}>
            <div><div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Grand Total</div>
              <div style={{ font: "700 24px Manrope", color: "#4ade80" }}>{fmtCurrency(data.grand_total)}</div></div>
            <div><div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>SKUs Valued</div>
              <div style={{ font: "700 24px Manrope" }}>{(data.items ?? data).length}</div></div>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Product</th><th>SKU</th><th>Category</th><th>Qty</th><th>Unit Cost</th><th>Total Value</th></tr></thead>
                <tbody>
                  {(data.items ?? data).map((r, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{r.product_name}</td>
                      <td className="font-mono td-muted">{r.sku}</td>
                      <td className="td-muted">{r.category ?? "—"}</td>
                      <td>{r.current_quantity}</td>
                      <td>{fmtCurrency(r.unit_cost)}</td>
                      <td style={{ fontWeight: 700, color: "#4ade80" }}>{fmtCurrency(r.total_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {data && tab === "status" && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Product</th><th>SKU</th><th>Status</th><th>In Stock</th><th>Reorder At</th><th>Shortfall</th></tr></thead>
              <tbody>
                {(data.items ?? data).map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{r.product_name}</td>
                    <td className="font-mono td-muted">{r.sku}</td>
                    <td>
                      <span style={{ fontSize: 11, fontWeight: 700, color: r.status === "healthy" ? "#4ade80" : r.status === "low_stock" ? "#fbbf24" : "#f87171" }}>
                        {r.status?.replace("_", " ")}
                      </span>
                    </td>
                    <td className="quantity">{r.current_quantity}</td>
                    <td className="td-muted">{r.reorder_point}</td>
                    <td style={{ color: r.shortfall > 0 ? "#f87171" : "var(--muted)" }}>{r.shortfall > 0 ? `-${r.shortfall}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!data && !loading && (
        <div className="card"><div className="empty"><div className="empty-icon">📊</div><p>Select a report type and click Generate Report</p></div></div>
      )}
    </div>
  );
}
