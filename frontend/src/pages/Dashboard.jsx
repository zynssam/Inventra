// src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import { Dashboard as DashboardAPI } from "../api";
import { StatCard, LoadingCenter, Badge, ForecastBadge } from "../components/ui";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Package, AlertTriangle, TrendingDown, DollarSign, Activity, ShoppingCart } from "lucide-react";

const COLORS = ["#5548e8","#22c55e","#f59e0b","#ef4444","#8b5cf6","#06b6d4"];

export default function Dashboard() {
  const [summary, setSummary]   = useState(null);
  const [alerts, setAlerts]     = useState([]);
  const [chart, setChart]       = useState([]);
  const [catVal, setCatVal]     = useState([]);
  const [recent, setRecent]     = useState([]);
  const [days, setDays]         = useState(30);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      DashboardAPI.summary(),
      DashboardAPI.alerts(),
      DashboardAPI.movementChart(days),
      DashboardAPI.categoryValue(),
      DashboardAPI.recentTransactions(),
    ]).then(([s, al, ch, cv, rt]) => {
      setSummary(s); setAlerts(al); setChart(ch); setCatVal(cv); setRecent(rt);
    }).catch(console.error).finally(() => setLoading(false));
  }, [days]);

  if (loading) return <LoadingCenter />;

  const fmtCurrency = v => `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
  const txnColor = type => type?.includes("in") || type === "po_receipt" ? "#4ade80" : type === "adjustment" ? "#fbbf24" : "#f87171";

  return (
    <div>
      {/* Stats */}
      <div className="stats-grid">
        <StatCard label="Total Products" value={summary?.total_products} icon={<Package size={18} />} />
        <StatCard label="Total Units" value={summary?.total_units?.toLocaleString()} icon={<Activity size={18} />} color="var(--green)" />
        <StatCard label="Inventory Value" value={fmtCurrency(summary?.total_inventory_value ?? 0)} icon={<DollarSign size={18} />} color="#22c55e" />
        <StatCard label="Low Stock" value={summary?.low_stock_count} icon={<AlertTriangle size={18} />} color="var(--amber)" />
        <StatCard label="Out of Stock" value={summary?.out_of_stock_count} icon={<TrendingDown size={18} />} color="var(--red)" />
        <StatCard label="Reorder Needed" value={summary?.reorder_needed_count} icon={<ShoppingCart size={18} />} color="var(--purple)" />
      </div>

      <div className="two-col" style={{ gap: 16, marginBottom: 16 }}>
        {/* Movement chart */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <span className="section-title" style={{ margin: 0 }}>Stock Movement</span>
            <select className="input" style={{ width: "auto", padding: "5px 10px", fontSize: 12 }} value={days} onChange={e => setDays(Number(e.target.value))}>
              {[7,14,30,90].map(d => <option key={d} value={d}>Last {d} days</option>)}
            </select>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chart} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
              <defs>
                <linearGradient id="gin" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4ade80" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#4ade80" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gout" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f87171" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#f87171" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#8890a8" }} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#8890a8" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#1e2132", border: "1px solid #2a2d3e", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="stock_in" stroke="#4ade80" fill="url(#gin)" strokeWidth={2} name="In" />
              <Area type="monotone" dataKey="stock_out" stroke="#f87171" fill="url(#gout)" strokeWidth={2} name="Out" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Category value donut */}
        <div className="card">
          <div className="section-title">Inventory by Category</div>
          {catVal.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={catVal} dataKey="value" nameKey="category" cx="50%" cy="50%" innerRadius={50} outerRadius={70} paddingAngle={3}>
                    {catVal.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#1e2132", border: "1px solid #2a2d3e", borderRadius: 8, fontSize: 12 }} formatter={v => [`$${Number(v).toFixed(0)}`, "Value"]} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px", marginTop: 8 }}>
                {catVal.map((c, i) => (
                  <span key={i} style={{ fontSize: 11, color: "var(--text-2)", display: "flex", alignItems: "center", gap: 5 }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS[i % COLORS.length], display: "inline-block" }} />
                    {c.category} <span style={{ color: "var(--muted)" }}>${Number(c.value).toFixed(0)}</span>
                  </span>
                ))}
              </div>
            </>
          ) : <div className="empty" style={{ padding: "40px 0" }}>No category data</div>}
        </div>
      </div>

      {/* Alerts + Recent transactions */}
      <div className="two-col" style={{ gap: 16 }}>
        <div className="card">
          <div className="section-title">Alerts</div>
          {alerts.length === 0
            ? <div className="empty" style={{ padding: "32px 0" }}>✅ All products are healthy</div>
            : <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {alerts.slice(0, 6).map((a, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{a.product_name}</div>
                      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{a.message}</div>
                    </div>
                    <Badge state={a.severity === "critical" ? "critical" : "warning"} label={a.severity} />
                  </div>
                ))}
              </div>
          }
        </div>

        <div className="card">
          <div className="section-title">Recent Transactions</div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Product</th><th>Type</th><th>Qty</th><th>Date</th></tr></thead>
              <tbody>
                {recent.slice(0, 8).map((t, i) => (
                  <tr key={i}>
                    <td>{t.product_name ?? "—"}</td>
                    <td><span style={{ fontSize: 11, color: txnColor(t.txn_type) }}>{t.txn_type?.replace("_", " ")}</span></td>
                    <td className="quantity" style={{ color: txnColor(t.txn_type) }}>
                      {t.quantity_delta > 0 ? "+" : ""}{t.quantity_delta}
                    </td>
                    <td className="td-muted">{new Date(t.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {recent.length === 0 && <div className="empty">No transactions yet</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
