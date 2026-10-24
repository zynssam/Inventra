// src/pages/Forecasts.jsx
import { useEffect, useState, useCallback } from "react";
import { Forecasts as API } from "../api";
import { PageHeader, ForecastBadge, Empty, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { TrendingUp, TrendingDown, Minus, Search, BarChart2, ChevronDown, ChevronUp } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";

const TREND_ICON = {
  rising:  <TrendingUp  size={14} color="#f87171" />,
  falling: <TrendingDown size={14} color="#4ade80" />,
  steady:  <Minus       size={14} color="#fbbf24" />,
};

const STATE_COLOR = {
  critical: "#f87171", out_of_stock: "#f87171",
  warning: "#fbbf24", ok: "#4ade80",
};

// ── Inline sparkline chart (usage bars + avg line + projection) ───────────────
function ForecastChart({ item }) {
  if (!item.daily_series || item.daily_series.length === 0) {
    return <div style={{ fontSize: 11, color: "var(--muted)", padding: "12px 0" }}>No daily usage data available for this window.</div>;
  }

  const avg = item.avg_daily_usage ?? 0;

  // Build projection days after the last data point
  const lastDate = item.daily_series[item.daily_series.length - 1]?.date;
  const projectionDays = item.days_until_stockout != null ? Math.min(Math.ceil(item.days_until_stockout), 14) : 0;
  const projections = [];
  if (lastDate && projectionDays > 0 && avg > 0) {
    let qty = item.current_quantity;
    for (let i = 1; i <= projectionDays; i++) {
      const d = new Date(lastDate);
      d.setDate(d.getDate() + i);
      qty = Math.max(0, qty - avg);
      projections.push({
        date: d.toISOString().slice(0, 10),
        projected_stock: Math.round(qty),
        used: null,
      });
    }
  }

  // Historical stock trajectory (reconstruct from current + usage)
  let qty = item.current_quantity;
  const histReverse = [...item.daily_series].reverse().map(d => {
    const stock = qty;
    qty += d.used; // add back (going backwards)
    return { date: d.date, used: d.used, stock };
  });
  const hist = histReverse.reverse().map((d, i) => ({
    date: d.date.slice(5),   // MM-DD
    used: d.used,
    stock: d.stock,
    avg: parseFloat(avg.toFixed(1)),
  }));

  const projChart = projections.map(p => ({
    date: p.date.slice(5),
    projected_stock: p.projected_stock,
  }));

  const stateColor = STATE_COLOR[item.state] ?? "var(--purple)";

  return (
    <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 8 }}>
      {/* Usage bars */}
      <div style={{ flex: "1 1 300px" }}>
        <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 6, fontWeight: 600, letterSpacing: 1 }}>
          DAILY USAGE (last {item.window_days}d)
        </div>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={hist} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 9, fill: "var(--muted)" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 9, fill: "var(--muted)" }} />
            <Tooltip
              contentStyle={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 11 }}
              labelStyle={{ color: "var(--text-2)", fontWeight: 600 }}
            />
            <Bar dataKey="used" fill="var(--purple)" opacity={0.8} radius={[2, 2, 0, 0]} name="Units Used" />
            <ReferenceLine y={avg} stroke={stateColor} strokeDasharray="4 2" label={{ value: `avg ${avg.toFixed(1)}`, fontSize: 9, fill: stateColor }} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Stock trajectory + projection */}
      <div style={{ flex: "1 1 300px" }}>
        <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 6, fontWeight: 600, letterSpacing: 1 }}>
          STOCK LEVEL + PROJECTION
        </div>
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart
            data={[...hist.map(h => ({ date: h.date, stock: h.stock })), ...projChart]}
            margin={{ top: 4, right: 4, bottom: 0, left: -20 }}
          >
            <defs>
              <linearGradient id={`sg-${item.product_id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={stateColor} stopOpacity={0.3} />
                <stop offset="100%" stopColor={stateColor} stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id={`pg-${item.product_id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#fbbf24" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 9, fill: "var(--muted)" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 9, fill: "var(--muted)" }} />
            <Tooltip
              contentStyle={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 11 }}
              labelStyle={{ color: "var(--text-2)", fontWeight: 600 }}
            />
            <Area dataKey="stock" stroke={stateColor} fill={`url(#sg-${item.product_id})`} strokeWidth={2} name="Actual Stock" dot={false} connectNulls />
            <Area dataKey="projected_stock" stroke="#fbbf24" fill={`url(#pg-${item.product_id})`} strokeWidth={2} strokeDasharray="5 3" name="Projected Stock" dot={false} connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Expandable row ────────────────────────────────────────────────────────────
function ForecastRow({ f }) {
  const [expanded, setExpanded] = useState(false);
  const fmtDate = iso => iso ? new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—";
  const stateColor = STATE_COLOR[f.state] ?? "var(--text)";
  const hasSeries = f.daily_series?.length > 0;

  return (
    <>
      <tr style={{ cursor: hasSeries ? "pointer" : "default" }} onClick={() => hasSeries && setExpanded(v => !v)}>
        <td>
          <div style={{ fontWeight: 600 }}>{f.product_name ?? `#${f.product_id}`}</div>
          <div className="td-muted font-mono">{f.sku}</div>
        </td>
        <td><ForecastBadge state={f.state} /></td>
        <td className="quantity">{f.current_quantity}</td>
        <td className="td-muted">{Number(f.avg_daily_usage ?? 0).toFixed(2)}/day</td>
        <td>
          {f.days_until_stockout != null
            ? <span style={{ fontWeight: 700, color: stateColor }}>{f.days_until_stockout.toFixed(1)}d</span>
            : <span className="td-muted">—</span>
          }
        </td>
        <td className="td-muted">{fmtDate(f.projected_stockout_date)}</td>
        <td>{TREND_ICON[f.trend] ?? <Minus size={14} color="var(--muted)" />}</td>
        <td className="td-muted" style={{ maxWidth: 220, whiteSpace: "normal", fontSize: 11 }}>{f.explanation ?? "—"}</td>
        <td style={{ width: 32, textAlign: "center" }}>
          {hasSeries && (
            <span style={{ color: "var(--muted)" }}>
              {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={9} style={{ background: "var(--surface-2)", padding: "14px 20px" }}>
            <ForecastChart item={f} />
          </td>
        </tr>
      )}
    </>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Forecasts() {
  const toast = useToast();
  const [items, setItems]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [stateFilter, setStateFilter] = useState("");
  const [win, setWin]           = useState(30);
  const [search, setSearch]     = useState("");

  const doFetch = useCallback(() => {
    setLoading(true);
    API.list({ window_days: win, ...(stateFilter ? { state: stateFilter } : {}) })
      .then(d => setItems(d.items ?? d))
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [win, stateFilter]);

  useEffect(() => { doFetch(); }, [doFetch]);

  const filtered = search
    ? items.filter(i => i.product_name?.toLowerCase().includes(search.toLowerCase()) || i.sku?.toLowerCase().includes(search.toLowerCase()))
    : items;

  // Summary KPIs
  const critical = items.filter(i => i.state === "critical" || i.state === "out_of_stock").length;
  const warning  = items.filter(i => i.state === "warning").length;
  const ok       = items.filter(i => i.state === "ok").length;

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Forecasts" subtitle="EWMA stockout predictions · click any row for charts" />

      {/* KPI strip */}
      {!loading && items.length > 0 && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          {[
            { label: "Critical / Out of Stock", value: critical, color: "#f87171" },
            { label: "Warning",                 value: warning,  color: "#fbbf24" },
            { label: "OK",                      value: ok,       color: "#4ade80" },
          ].map(k => (
            <div key={k.label} style={{
              flex: "1 1 140px", background: "var(--surface)", border: "1px solid var(--line)",
              borderRadius: 12, padding: "14px 18px",
              borderLeft: `3px solid ${k.color}`,
            }}>
              <div style={{ font: `700 22px Manrope`, color: k.color }}>{k.value}</div>
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{k.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="toolbar">
        <div className="toolbar-left">
          <div className="search-wrap">
            <Search size={14} />
            <input className="input" placeholder="Search product…" value={search}
              onChange={e => setSearch(e.target.value)} style={{ minWidth: 200 }} />
          </div>
          <select className="input" style={{ width: "auto" }} value={stateFilter}
            onChange={e => setStateFilter(e.target.value)}>
            <option value="">All States</option>
            {["ok","warning","critical","out_of_stock","insufficient_data","no_recent_usage"].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </select>
          <select className="input" style={{ width: "auto" }} value={win}
            onChange={e => setWin(Number(e.target.value))}>
            {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>Window: {d} days</option>)}
          </select>
        </div>
        <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", alignItems: "center", gap: 4 }}>
          <BarChart2 size={12} /> Click a row to expand chart
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th><th>State</th><th>Qty In Stock</th>
                <th>Avg Daily</th><th>Days Left</th>
                <th>Projected Date</th><th>Trend</th><th>Explanation</th><th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={9}><Empty icon="📈" message="No forecast data" /></td></tr>
              ) : filtered.map(f => (
                <ForecastRow key={f.product_id} f={f} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
