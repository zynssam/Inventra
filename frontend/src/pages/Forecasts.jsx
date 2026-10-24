// src/pages/Forecasts.jsx
import { useEffect, useState, useCallback } from "react";
import { Forecasts as API } from "../api";
import { PageHeader, ForecastBadge, Empty, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { TrendingUp, TrendingDown, Minus, Search } from "lucide-react";

const TREND_ICON = { rising: <TrendingUp size={14} color="#f87171" />, falling: <TrendingDown size={14} color="#4ade80" />, steady: <Minus size={14} color="#fbbf24" /> };

export default function Forecasts() {
  const toast = useToast();
  const [items, setItems]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [stateFilter, setStateFilter] = useState("");
  const [window, setWindow]     = useState(30);
  const [search, setSearch]     = useState("");

  const fetch = useCallback(() => {
    setLoading(true);
    API.list({ window_days: window, ...(stateFilter ? { state: stateFilter } : {}) })
      .then(d => setItems(d.items ?? d))
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [window, stateFilter]);

  useEffect(() => { fetch(); }, [fetch]);

  const filtered = search ? items.filter(i => i.product_name?.toLowerCase().includes(search.toLowerCase()) || i.sku?.toLowerCase().includes(search.toLowerCase())) : items;
  const fmtDate = iso => iso ? new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—";

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Forecasts" subtitle="Stockout predictions based on usage history" />

      <div className="toolbar">
        <div className="toolbar-left">
          <div className="search-wrap">
            <Search size={14} />
            <input className="input" placeholder="Search product…" value={search} onChange={e => setSearch(e.target.value)} style={{ minWidth: 200 }} />
          </div>
          <select className="input" style={{ width: "auto" }} value={stateFilter} onChange={e => setStateFilter(e.target.value)}>
            <option value="">All States</option>
            {["ok","warning","critical","out_of_stock","insufficient_data"].map(s => (
              <option key={s} value={s}>{s.replace("_", " ")}</option>
            ))}
          </select>
          <select className="input" style={{ width: "auto" }} value={window} onChange={e => setWindow(Number(e.target.value))}>
            {[7,14,30,60].map(d => <option key={d} value={d}>Window: {d} days</option>)}
          </select>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th><th>State</th><th>Qty In Stock</th>
                <th>Avg Daily Usage</th><th>Days Until Stockout</th>
                <th>Projected Date</th><th>Trend</th><th>Explanation</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="8"><Empty icon="📈" message="No forecast data" /></td></tr>
              ) : filtered.map(f => (
                <tr key={f.product_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{f.product_name}</div>
                    <div className="td-muted font-mono">{f.sku}</div>
                  </td>
                  <td><ForecastBadge state={f.state} /></td>
                  <td className="quantity">{f.current_quantity}</td>
                  <td className="td-muted">{Number(f.avg_daily_usage ?? 0).toFixed(2)}/day</td>
                  <td>
                    {f.days_until_stockout != null
                      ? <span style={{ fontWeight: 700, color: f.state === "critical" || f.state === "out_of_stock" ? "#f87171" : f.state === "warning" ? "#fbbf24" : "#4ade80" }}>
                          {f.days_until_stockout}d
                        </span>
                      : <span className="td-muted">—</span>
                    }
                  </td>
                  <td className="td-muted">{fmtDate(f.projected_stockout_date)}</td>
                  <td>{TREND_ICON[f.trend] ?? <Minus size={14} color="var(--muted)" />}</td>
                  <td className="td-muted" style={{ maxWidth: 240, whiteSpace: "normal", fontSize: 11 }}>{f.explanation ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
