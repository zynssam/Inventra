// src/components/Chatbot.jsx
// Simple rule-based AI assistant for Inventra — no external API needed
import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Bot, ChevronDown } from "lucide-react";

// ── Knowledge base ───────────────────────────────────────────────────────────
const KB = [
  {
    patterns: ["hello", "hi", "hey", "help", "start", "what can you do"],
    answer: "Hi! I'm Invy 🤖, your Inventra assistant. I can help you with:\n\n• **Products** — adding, editing, searching\n• **Transactions** — stock in/out, adjustments\n• **Forecasts** — understanding stockout predictions\n• **Reorder** — recommendations and simulation\n• **Reports** — generating and exporting\n• **Settings** — configuring thresholds\n\nWhat would you like to know?",
  },
  {
    patterns: ["add product", "create product", "new product"],
    answer: "To add a product:\n1. Go to **Products** in the sidebar\n2. Click **Add Product** (top-right)\n3. Fill in: Name, SKU, Unit, Unit Cost, Category, Supplier\n4. Set **Reorder Point** — the quantity that triggers a reorder alert\n5. Click **Save Product**\n\n> Only Admins and Store Managers can create products.",
  },
  {
    patterns: ["stock in", "receive stock", "add stock", "po receipt"],
    answer: "To record stock coming in:\n1. Go to **Transactions**\n2. Click **Stock In** (top-right)\n3. Select the product, enter quantity, choose type (Stock In or PO Receipt)\n4. Add an optional reason, then **Confirm**\n\nEvery entry is logged in the Audit Log automatically.",
  },
  {
    patterns: ["stock out", "remove stock", "issue stock", "use stock"],
    answer: "To record stock going out:\n1. Go to **Transactions**\n2. Click **Stock Out**\n3. Select product, enter quantity\n4. Choose type: **Stock Out** (general) or **Stocktake** (count-based)\n5. Confirm — the balance updates instantly.",
  },
  {
    patterns: ["adjust", "adjustment", "correct quantity", "fix stock"],
    answer: "To manually correct stock quantity (Admin only):\n1. Go to **Transactions**\n2. Click **Adjust**\n3. Select the product, enter the **new absolute quantity**\n4. Add a reason and confirm\n\nThis creates an adjustment entry to keep the audit trail intact.",
  },
  {
    patterns: ["reverse", "undo transaction", "cancel transaction"],
    answer: "To reverse a transaction:\n1. Go to **Transactions**\n2. Find the transaction row and click the **↩ reverse** icon\n3. Enter a reason\n\nThis creates an opposing entry — no data is deleted. Only non-reversed transactions can be reversed.",
  },
  {
    patterns: ["forecast", "prediction", "stockout", "run out", "days left"],
    answer: "Forecasts predict when each product will run out based on recent usage:\n\n• **OK** 🟢 — plenty of stock\n• **Warning** 🟡 — stockout within warning threshold (default 14 days)\n• **Critical** 🔴 — stockout within critical threshold (default 7 days)\n• **Out of Stock** — quantity is 0\n• **No Data / No Usage** — not enough history to forecast\n\nGo to **Forecasts** to see all products. Use the window filter to change the analysis period.",
  },
  {
    patterns: ["reorder", "recommendation", "what to buy", "replenish"],
    answer: "Reorder recommendations tell you what to buy and how much:\n\n1. Go to **Reorder** in the sidebar\n2. Change **Target Days** to plan for different periods\n3. Enable **Show all products** to see items with no urgent need\n4. Click **Simulate** to run a what-if scenario with different parameters\n\nThe **Total Estimated Cost** banner shows the total purchasing cost.",
  },
  {
    patterns: ["simulate", "what if", "simulation"],
    answer: "The **What-If Simulation** lets you explore reorder scenarios:\n\n1. Go to **Reorder**\n2. Click **Simulate** (top-right)\n3. Adjust: Target Days, Window Days, Lead Time, Safety Days\n4. Click **Run Simulation** to see projected quantities and costs\n\nUseful for planning ahead before placing purchase orders.",
  },
  {
    patterns: ["report", "export", "csv", "download"],
    answer: "To generate a report:\n1. Go to **Reports** in the sidebar\n2. Choose a report tab:\n   - **Stock Movements** — transaction history with date/type filters\n   - **Inventory Valuation** — stock value by product\n   - **Stock Status** — current status of all products\n3. Click **Generate Report** to see it in-browser\n4. Click **Export CSV** to download\n\nAll report types support CSV download.",
  },
  {
    patterns: ["setting", "threshold", "warning days", "critical days", "window"],
    answer: "Settings control how forecasts are calculated:\n\n| Setting | Default | Description |\n|---|---|---|\n| Usage Window | 30 days | How far back to look for usage |\n| Warning Days | 14 | Days left that triggers Warning |\n| Critical Days | 7 | Days left that triggers Critical |\n| Min Usage Days | 7 | Min data needed for a forecast |\n| Target Days | 30 | Default reorder planning horizon |\n\nGo to **Settings** to change them. Only Admins can save changes.",
  },
  {
    patterns: ["user", "role", "permission", "access", "admin", "manager", "viewer"],
    answer: "Inventra has three roles:\n\n| Role | Can do |\n|---|---|\n| **Admin** | Everything — users, settings, adjustments, delete |\n| **Store Manager** | Stock in/out, products, categories, suppliers |\n| **Viewer** | Read-only — view all data, generate reports |\n\nGo to **Users** (admin only) to create or manage user accounts.",
  },
  {
    patterns: ["category", "categories"],
    answer: "Categories group products together:\n1. Go to **Categories** in the sidebar\n2. Click **Add Category**, enter a name and optional description\n3. Assign a category when creating or editing a product\n\nCategories are also used in the **Inventory Valuation** report and the **Dashboard** donut chart.",
  },
  {
    patterns: ["supplier", "vendor", "supplier management"],
    answer: "Suppliers store vendor info for each product:\n1. Go to **Suppliers**\n2. Click **Add Supplier** — fill in name, email, phone, lead time\n3. Assign a supplier to a product — the lead time is used in reorder calculations\n\nLead time affects how many days ahead you need to place an order.",
  },
  {
    patterns: ["audit", "audit log", "history", "who changed", "track"],
    answer: "The **Audit Log** (admin only) records every important action:\n\n• Product creates, updates, archives\n• Stock transactions\n• User changes\n• Settings updates\n\nGo to **Audit Log** and filter by action, entity type, or date range.",
  },
  {
    patterns: ["dashboard", "overview", "summary", "home"],
    answer: "The **Dashboard** gives a real-time overview:\n\n• **KPI tiles** — total products, units, value, low stock, out of stock, reorder needed\n• **Stock Movement chart** — in vs out over time (7/14/30/90 days)\n• **Category Value donut** — inventory value by category\n• **Alerts** — products needing attention\n• **Recent Transactions** — latest 8 movements\n\nAll data updates each time you visit the page.",
  },
  {
    patterns: ["low stock", "alert", "critical", "out of stock"],
    answer: "Stock alerts are shown on the **Dashboard** and the **Forecasts** page:\n\n• **Low Stock** — quantity is at or below the reorder point\n• **Out of Stock** — quantity is 0\n• **Warning** — forecast shows stockout within 14 days\n• **Critical** — forecast shows stockout within 7 days\n\nGo to **Reorder** to see what needs to be purchased.",
  },
  {
    patterns: ["demo", "test", "sample data", "seed"],
    answer: "To load demo data for testing:\n```\ncurl -X POST http://localhost:8000/api/v1/dev/seed-demo\n```\n> Requires `DEBUG=true` in `backend/.env`\n\nThis creates 3 demo accounts, 6 products across 4 categories, stock history, and 1 open PO.\n\nDemo logins:\n• admin@inventra.dev / admin123\n• store@inventra.dev / store123\n• viewer@inventra.dev / viewer123",
  },
];

const SUGGESTIONS = [
  "How do I add a product?",
  "What do the forecast states mean?",
  "How do I stock in?",
  "How do reports work?",
];

function findAnswer(input) {
  const q = input.toLowerCase().trim();
  for (const entry of KB) {
    if (entry.patterns.some(p => q.includes(p))) return entry.answer;
  }
  return "I'm not sure about that yet! Try asking about:\n\n• Products, transactions, or stock adjustments\n• Forecasts or reorder recommendations\n• Reports, settings, or user roles\n• The audit log or dashboard";
}

// Simple markdown-like renderer (bold, code, tables, bullets)
function renderMd(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code style='background:var(--surface-3);padding:1px 5px;border-radius:3px;font-size:11px'>$1</code>")
    .replace(/\n/g, "<br/>");
}

export default function Chatbot() {
  const [open, setOpen]     = useState(false);
  const [messages, setMessages] = useState([
    { from: "bot", text: "Hi! I'm **Invy** 🤖 — your Inventra assistant.\n\nAsk me anything about using the app!" }
  ]);
  const [input, setInput]   = useState("");
  const [typing, setTyping] = useState(false);
  const bottomRef           = useRef(null);
  const inputRef            = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 200);
  }, [open]);

  function send(text) {
    const q = (text ?? input).trim();
    if (!q) return;
    setMessages(m => [...m, { from: "user", text: q }]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMessages(m => [...m, { from: "bot", text: findAnswer(q) }]);
    }, 600 + Math.random() * 400);
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          position: "fixed", bottom: 28, right: 28, zIndex: 300,
          width: 52, height: 52, borderRadius: "50%",
          background: "linear-gradient(135deg, var(--purple), #7c6ced)",
          border: "none", cursor: "pointer", color: "#fff",
          boxShadow: "0 4px 24px #5548e850",
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "transform 0.2s, box-shadow 0.2s",
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.1)"; e.currentTarget.style.boxShadow = "0 6px 32px #5548e870"; }}
        onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; e.currentTarget.style.boxShadow = "0 4px 24px #5548e850"; }}
        title="Ask Invy"
      >
        {open ? <ChevronDown size={22} /> : <MessageCircle size={22} />}
      </button>

      {/* Chat window */}
      {open && (
        <div style={{
          position: "fixed", bottom: 92, right: 28, zIndex: 300,
          width: 360, maxHeight: "75vh",
          background: "var(--surface)", border: "1px solid var(--line)",
          borderRadius: 18, display: "flex", flexDirection: "column",
          boxShadow: "0 20px 60px #00000080",
          animation: "slideUp 0.2s ease",
          overflow: "hidden",
        }}>
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "14px 18px", borderBottom: "1px solid var(--line)",
            background: "linear-gradient(135deg, var(--purple), #7c6ced)",
          }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#ffffff25", display: "grid", placeItems: "center" }}>
              <Bot size={17} color="#fff" />
            </div>
            <div>
              <div style={{ font: "700 13px Manrope", color: "#fff" }}>Invy — Inventra Assistant</div>
              <div style={{ fontSize: 10, color: "#d4d0ff" }}>Always online · Knows Inventra inside out</div>
            </div>
            <button onClick={() => setOpen(false)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "#fff", opacity: 0.7 }}><X size={16} /></button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: m.from === "user" ? "flex-end" : "flex-start" }}>
                {m.from === "bot" && (
                  <div style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--purple-glow)", border: "1px solid var(--purple)", display: "grid", placeItems: "center", flexShrink: 0, marginRight: 7, marginTop: 2 }}>
                    <Bot size={13} color="var(--purple)" />
                  </div>
                )}
                <div style={{
                  maxWidth: "82%",
                  padding: "9px 13px",
                  borderRadius: m.from === "user" ? "14px 14px 4px 14px" : "4px 14px 14px 14px",
                  background: m.from === "user" ? "var(--purple)" : "var(--surface-3)",
                  color: m.from === "user" ? "#fff" : "var(--text)",
                  fontSize: 12,
                  lineHeight: 1.6,
                  border: m.from === "bot" ? "1px solid var(--line)" : "none",
                }}
                  dangerouslySetInnerHTML={{ __html: renderMd(m.text) }}
                />
              </div>
            ))}
            {typing && (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--purple-glow)", border: "1px solid var(--purple)", display: "grid", placeItems: "center" }}>
                  <Bot size={13} color="var(--purple)" />
                </div>
                <div style={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: "4px 14px 14px 14px", padding: "10px 14px", display: "flex", gap: 4, alignItems: "center" }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--purple)", animation: `bounce 1s ${i * 0.2}s infinite` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions */}
          {messages.length <= 1 && (
            <div style={{ padding: "0 14px 10px", display: "flex", flexWrap: "wrap", gap: 6 }}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => send(s)} style={{
                  fontSize: 10, padding: "5px 10px",
                  background: "var(--surface-3)", border: "1px solid var(--line)",
                  borderRadius: 99, color: "var(--text-2)", cursor: "pointer",
                  transition: "border-color 0.15s",
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = "var(--purple)"}
                  onMouseLeave={e => e.currentTarget.style.borderColor = "var(--line)"}
                >{s}</button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{ padding: "10px 14px", borderTop: "1px solid var(--line)", display: "flex", gap: 8 }}>
            <input
              ref={inputRef}
              className="input"
              style={{ flex: 1, fontSize: 12, padding: "8px 12px" }}
              placeholder="Ask anything about Inventra…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && send()}
            />
            <button className="btn btn-primary btn-icon" onClick={() => send()} disabled={!input.trim()}>
              <Send size={14} />
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-5px); }
        }
      `}</style>
    </>
  );
}
