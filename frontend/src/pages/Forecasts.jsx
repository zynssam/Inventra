// src/pages/Forecasts.jsx
import { useEffect, useState, useCallback, useRef } from "react";
import { Forecasts as API } from "../api";
import { PageHeader, ForecastBadge, Empty, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { TrendingUp, TrendingDown, Minus, Search, BarChart2, ChevronDown, ChevronUp } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
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

// ── Build chart data from a forecast item ─────────────────────────────────────
function buildChartData(item) {
  if (!item.daily_series || item.daily_series.length === 0) return { hist: [], proj: [] };

  const avg = item.avg_daily_usage ?? 0;

  // Reconstruct historical stock levels (walk backward from current qty)
  let qty = item.current_quantity;
  const histReverse = [...item.daily_series].reverse().map(d => {
    const stock = qty;
    qty += d.used;
    return { date: d.date.slice(5), used: d.used, stock, avg: parseFloat(avg.toFixed(1)) };
  });
  const hist = histReverse.reverse();

  // Projection forward
  const lastDate = item.daily_series[item.daily_series.length - 1]?.date;
  const projDays = item.days_until_stockout != null ? Math.min(Math.ceil(item.days_until_stockout), 10) : 0;
  const proj = [];
  if (lastDate && projDays > 0 && avg > 0) {
    let pQty = item.current_quantity;
    for (let i = 1; i <= projDays; i++) {
      const d = new Date(lastDate);
      d.setDate(d.getDate() + i);
      pQty = Math.max(0, pQty - avg);
      proj.push({ date: d.toISOString().slice(5, 10), projected_stock: Math.round(pQty) });
    }
  }
  return { hist, proj };
}

// ── Hover popup chart ─────────────────────────────────────────────────────────
function HoverChart({ item, pos }) {
  if (!item) return null;
  const { hist, proj } = buildChartData(item);
  const stateColor = STATE_COLOR[item.state] ?? "var(--purple)";
  const avg = item.avg_daily_usage ?? 0;
  const hasSeries = hist.length > 0;

  // Smart positioning — keep popup on screen
  const POPUP_W = 420, POPUP_H = 260;
  const vw = window.innerWidth, vh = window.innerHeight;
  let left = pos.x + 16;
  let top  = pos.y - 40;
  if (left + POPUP_W > vw - 12) left = pos.x - POPUP_W - 16;
  if (top + POPUP_H > vh - 12) top = vh - POPUP_H - 12;
  if (top < 8) top = 8;

  return (
    <div style={{
      position: "fixed", top, left, zIndex: 500,
      width: POPUP_W,
      background: "var(--surface)",
      border: "1px solid var(--line)",
      borderRadius: 16,
      boxShadow: "0 20px 60px #00000090",
      pointerEvents: "none",
      animation: "fadeInPop 0.15s ease",
      overflow: "hidden",
    }}>
      {/* Header strip */}
      <div style={{
        padding: "10px 16px 8px",
        background: "var(--surface-2)",
        borderBottom: "1px solid var(--line)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div>
          <span style={{ fontWeight: 700, fontSize: 13 }}>{item.product_name ?? `#${item.product_id}`}</span>
          <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: 8, fontFamily: "monospace" }}>{item.sku}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <ForecastBadge state={item.state} />
          <span style={{ fontSize: 11, color: "var(--muted)" }}>
            {item.days_until_stockout != null
              ? <><span style={{ color: stateColor, fontWeight: 700 }}>{item.days_until_stockout.toFixed(1)}d</span> left</>
              : "—"
            }
          </span>
        </div>
      </div>

      {/* Charts */}
      <div style={{ padding: "10px 12px 12px", display: "flex", gap: 10 }}>
        {!hasSeries ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", height: 140, fontSize: 12, color: "var(--muted)" }}>
            No daily usage data for this window
          </div>
        ) : (
          <>
            {/* Usage sparkline */}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, color: "var(--muted)", marginBottom: 4, fontWeight: 700, letterSpacing: 0.8 }}>DAILY USAGE</div>
              <ResponsiveContainer width="100%" height={130}>
                <BarChart data={hist} margin={{ top: 4, right: 2, bottom: 0, left: -28 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 8, fill: "var(--muted)" }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 8, fill: "var(--muted)" }} />
                  <Tooltip
                    contentStyle={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 6, fontSize: 10 }}
                    labelStyle={{ color: "var(--text-2)", fontWeight: 600 }}
                  />
                  <Bar dataKey="used" fill="var(--purple)" opacity={0.85} radius={[2, 2, 0, 0]} name="Used" />
                  {avg > 0 && (
                    <ReferenceLine y={avg} stroke={stateColor} strokeDasharray="4 2"
                      label={{ value: `~${avg.toFixed(1)}/d`, fontSize: 8, fill: stateColor, position: "right" }} />
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Stock projection */}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, color: "var(--muted)", marginBottom: 4, fontWeight: 700, letterSpacing: 0.8 }}>STOCK PROJECTION</div>
              <ResponsiveContainer width="100%" height={130}>
                <AreaChart
                  data={[...hist.map(h => ({ date: h.date, stock: h.stock })), ...proj]}
                  margin={{ top: 4, right: 2, bottom: 0, left: -28 }}
                >
                  <defs>
                    <linearGradient id={`hg-${item.product_id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={stateColor} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={stateColor} stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id={`hp-${item.product_id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#fbbf24" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 8, fill: "var(--muted)" }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 8, fill: "var(--muted)" }} />
                  <Tooltip
                    contentStyle={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 6, fontSize: 10 }}
                    labelStyle={{ color: "var(--text-2)", fontWeight: 600 }}
                  />
                  <Area dataKey="stock" stroke={stateColor} fill={`url(#hg-${item.product_id})`}
                    strokeWidth={2} name="Actual Stock" dot={false} connectNulls />
                  <Area dataKey="projected_stock" stroke="#fbbf24" fill={`url(#hp-${item.product_id})`}
                    strokeWidth={2} strokeDasharray="5 3" name="Projected" dot={false} connectNulls />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div style={{ padding: "6px 16px 10px", fontSize: 10, color: "var(--muted)", borderTop: "1px solid var(--line)" }}>
        {item.explanation}
      </div>
    </div>
  );
}

// ── Inline expanded chart (click-to-expand) ───────────────────────────────────
function ForecastChart({ item }) {
  const { hist, proj } = buildChartData(item);
  const stateColor = STATE_COLOR[item.state] ?? "var(--purple)";
  const avg = item.avg_daily_usage ?? 0;

  if (hist.length === 0) {
    return <div style={{ fontSize: 12, color: "var(--muted)", padding: "10px 0" }}>No daily usage data for this window.</div>;
  }

  return (
    <div style={{ display: "flex", gap: 20, flexWrap: "wrap", paddingTop: 4 }}>
      <div style={{ flex: "1 1 280px" }}>
        <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 6, fontWeight: 700, letterSpacing: 1 }}>DAILY USAGE (last {item.window_days}d)</div>
        <ResponsiveContainer width="100%" height={130}>
          <BarChart data={hist} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 9, fill: "var(--muted)" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 9, fill: "var(--muted)" }} />
            <Tooltip contentStyle={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 11 }} />
            <Bar dataKey="used" fill="var(--purple)" opacity={0.85} radius={[2, 2, 0, 0]} name="Units Used" />
            {avg > 0 && <ReferenceLine y={avg} stroke={stateColor} strokeDasharray="4 2"
              label={{ value: `avg ${avg.toFixed(1)}/d`, fontSize: 9, fill: stateColor }} />}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div style={{ flex: "1 1 280px" }}>
        <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 6, fontWeight: 700, letterSpacing: 1 }}>STOCK LEVEL + PROJECTION</div>
        <ResponsiveContainer width="100%" height={130}>
          <AreaChart data={[...hist.map(h => ({ date: h.date, stock: h.stock })), ...proj]}
            margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
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
            <Tooltip contentStyle={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 11 }} />
            <Area dataKey="stock" stroke={stateColor} fill={`url(#sg-${item.product_id})`} strokeWidth={2} name="Stock" dot={false} connectNulls />
            <Area dataKey="projected_stock" stroke="#fbbf24" fill={`url(#pg-${item.product_id})`} strokeWidth={2} strokeDasharray="5 3" name="Projected" dot={false} connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Row with hover + click expand ─────────────────────────────────────────────
function ForecastRow({ f, onHover, onLeave }) {
  const [expanded, setExpanded] = useState(false);
  const fmtDate = iso => iso ? new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—";
  const stateColor = STATE_COLOR[f.state] ?? "var(--text)";

  return (
    <>
      <tr
        style={{ cursor: "pointer", transition: "background 0.1s" }}
        onClick={() => setExpanded(v => !v)}
        onMouseEnter={e => onHover(f, e)}
        onMouseMove={e => onHover(f, e)}
        onMouseLeave={onLeave}
      >
        <td>
          <div style={{ fontWeight: 600 }}>{f.product_name ?? `#${f.product_id}`}</div>
          <div className="td-muted font-mono" style={{ fontSize: 10 }}>{f.sku}</div>
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
        <td style={{ width: 28, textAlign: "center", color: "var(--muted)" }}>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </td>
      </tr>
      {expanded && (
        <tr onMouseEnter={onLeave}>
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
  const [items, setItems]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [stateFilter, setStateFilter] = useState("");
  const [win, setWin]             = useState(30);
  const [search, setSearch]       = useState("");

  // Hover state
  const [hovered, setHovered]   = useState(null);  // forecast item
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const hoverTimer = useRef(null);

  const doFetch = useCallback(() => {
    setLoading(true);
    API.list({ window_days: win, ...(stateFilter ? { state: stateFilter } : {}) })
      .then(d => setItems(d.items ?? d))
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [win, stateFilter]);

  useEffect(() => { doFetch(); }, [doFetch]);

  const filtered = search
    ? items.filter(i =>
        i.product_name?.toLowerCase().includes(search.toLowerCase()) ||
        i.sku?.toLowerCase().includes(search.toLowerCase()))
    : items;

  const critical = items.filter(i => ["critical","out_of_stock"].includes(i.state)).length;
  const warning  = items.filter(i => i.state === "warning").length;
  const ok       = items.filter(i => i.state === "ok").length;

  function handleHover(item, e) {
    clearTimeout(hoverTimer.current);
    setHoverPos({ x: e.clientX, y: e.clientY });
    // Small delay before showing — avoids flicker when moving across rows
    hoverTimer.current = setTimeout(() => setHovered(item), 120);
  }
  function handleLeave() {
    clearTimeout(hoverTimer.current);
    setHovered(null);
  }

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Forecasts" subtitle="EWMA stockout predictions · hover for chart · click to expand" />

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
              borderRadius: 12, padding: "14px 18px", borderLeft: `3px solid ${k.color}`,
            }}>
              <div style={{ font: "700 22px Manrope", color: k.color }}>{k.value}</div>
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
            {[7,14,30,60,90].map(d => <option key={d} value={d}>Window: {d} days</option>)}
          </select>
        </div>
        <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", alignItems: "center", gap: 4 }}>
          <BarChart2 size={12} /> Hover = mini chart · Click = full chart
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
                <ForecastRow key={f.product_id} f={f} onHover={handleHover} onLeave={handleLeave} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hover popup — rendered as fixed overlay */}
      <HoverChart item={hovered} pos={hoverPos} />

      <style>{`
        @keyframes fadeInPop {
          from { opacity: 0; transform: scale(0.96) translateY(4px); }
          to   { opacity: 1; transform: scale(1)    translateY(0); }
        }
      `}</style>
    </div>
  );
}
