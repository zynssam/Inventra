// src/components/Chatbot.jsx
// Invy — Inventra AI Assistant powered by Google Gemini (free tier)
// Falls back to enhanced local KB if no API key is configured.
import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Bot, ChevronDown, Sparkles } from "lucide-react";

// ── Gemini configuration ──────────────────────────────────────────────────────
// Add VITE_GEMINI_API_KEY=your_key to frontend/.env
const GEMINI_KEY = import.meta.env.VITE_GEMINI_API_KEY;
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}`;

const SYSTEM_PROMPT = `You are Invy, the AI assistant for Inventra — an inventory management system.
Be concise, helpful, and friendly. Use bullet points when listing steps.
Inventra features:
- Products (add/edit/archive, SKU, reorder points, QR codes)
- Transactions (stock in, stock out, adjustment, reversal, PO receipt, stocktake)
- Forecasts (EWMA stockout predictions, daily usage charts, states: ok/warning/critical/out_of_stock)
- Reorder recommendations + What-If simulation
- Categories, Suppliers management
- Reports (Stock Movements, Inventory Valuation, Stock Status) with CSV export
- Settings (usage window, warning/critical threshold days)
- Users & Roles: Admin (full access), Store Manager (stock ops), Viewer (read-only)
- Audit Log (admin only — tracks all actions)
- Dashboard (KPIs, stock movement chart, category donut, alerts)
- QR scanner: camera or upload image to auto-fill transactions
Demo accounts: admin@inventra.dev/admin123, store@inventra.dev/store123, viewer@inventra.dev/viewer123
Answer only questions related to Inventra. For unrelated topics, politely redirect.
Keep responses under 200 words unless the question requires detail.`;

// ── Local KB fallback (runs when no API key or Gemini fails) ─────────────────
const KB = [
  { p: /product|sku|item|inventory|catalog|add.*product|create.*product/i, a: "**Products** — Go to **Products** in the sidebar.\n• **Add**: Click *Add Product*, fill in Name, SKU, Unit, Unit Cost, Category, Supplier and Reorder Point.\n• **Edit**: Click the ✏️ icon on any row.\n• **QR Code**: Click the QR badge in any row to view & download the product's QR code.\n• **Archive**: Admin-only, hides the product from active inventory." },
  { p: /stock.?in|receive|incoming|po.?receipt|add.*stock/i, a: "**Stock In** — Go to **Transactions** → click *Stock In*.\n• Select a product (or click *Scan QR* to scan the label)\n• Enter quantity\n• Choose type: *Stock In* or *PO Receipt*\n• Add an optional reason → **Confirm**" },
  { p: /stock.?out|issue|use.*stock|remove.*stock|outgoing/i, a: "**Stock Out** — Go to **Transactions** → click *Stock Out*.\n• Select a product (or scan its QR code)\n• Enter quantity used\n• Choose type: *Stock Out* or *Stocktake*\n• Confirm. The balance updates instantly." },
  { p: /adjust|correction|fix.*stock|wrong.*quantity/i, a: "**Adjust Quantity** (Admin only) — Go to **Transactions** → *Adjust*.\n• Select product\n• Enter the **new absolute quantity**\n• Add a reason (recommended)\nAn adjustment entry is created to preserve the audit trail." },
  { p: /revers|undo|cancel.*transaction/i, a: "**Reverse a Transaction** — Find the row in **Transactions**, click the ↩ icon and enter a reason.\nThis creates an opposing entry — no data is deleted. Only non-reversed transactions can be reversed." },
  { p: /forecast|stockout|run.*out|days.*left|predict|ewma/i, a: "**Forecasts** — Uses EWMA (Exponential Weighted Moving Average) to predict stockout dates.\n\n| State | Meaning |\n|---|---|\n| 🟢 OK | Plenty of stock |\n| 🟡 Warning | Stockout within 14 days |\n| 🔴 Critical | Stockout within 7 days |\n| Out of Stock | Qty = 0 |\n| No Data | Not enough history |\n\nClick any row to expand usage charts and the stock projection graph." },
  { p: /reorder|recommend|what.*buy|replenish|simulation|simulate/i, a: "**Reorder Recommendations** — Go to **Reorder**.\n• Set *Target Days* to plan how many days of stock to maintain\n• Click *Simulate* to run a What-If with custom window/lead-time/safety-stock\n• Total Estimated Cost is shown at the top\n• *Show all products* toggle includes items with no urgent need" },
  { p: /report|export|csv|download|valuation|movement/i, a: "**Reports** — Go to **Reports** and pick a tab:\n• **Stock Movements** — transaction history (filter by date/type)\n• **Inventory Valuation** — current stock value by product\n• **Stock Status** — snapshot of all product statuses\n\nClick *Generate Report* then *Export CSV* to download." },
  { p: /setting|threshold|warning.*day|critical.*day|window.*day|usage.*window/i, a: "**Settings** (Admin only) — Go to **Settings**.\n\n| Setting | Default |\n|---|---|\n| Usage Window | 30 days of history used |\n| Warning Days | 14 days — triggers Warning state |\n| Critical Days | 7 days — triggers Critical state |\n| Min Usage Days | 7 — minimum data for a forecast |\n| Target Days | 30 — default reorder horizon |" },
  { p: /user|role|permission|admin|manager|viewer|access/i, a: "**User Roles** — Go to **Users** (Admin only) to manage.\n\n| Role | Can do |\n|---|---|\n| Admin | Everything |\n| Store Manager | Stock in/out, products, categories, suppliers |\n| Viewer | Read-only — view + export reports |" },
  { p: /categor/i, a: "**Categories** — Group products together.\n• Go to **Categories** → *Add Category*\n• Assign categories when creating/editing products\n• Used in the Dashboard donut chart and Inventory Valuation report" },
  { p: /supplier|vendor|lead.?time/i, a: "**Suppliers** — Store vendor info for each product.\n• Go to **Suppliers** → *Add Supplier* (name, email, phone, lead time)\n• Lead time affects reorder calculations\n• Each product can be assigned one supplier" },
  { p: /audit|log|history|who|track|change/i, a: "**Audit Log** (Admin only) — Records every important action:\n• Product creates, updates, archives\n• All stock transactions\n• User account changes\n• Settings updates\n\nFilter by action type, entity, or date range." },
  { p: /dashboard|overview|home|summary|kpi/i, a: "**Dashboard** — Real-time inventory overview:\n• KPI tiles: total products, units, value, low stock, out of stock\n• Stock Movement chart (in vs out: 7/14/30/90 day view)\n• Category Value donut chart\n• Recent alerts + last 8 transactions" },
  { p: /qr|scan|scanner|barcode/i, a: "**QR Codes** — Every product has a QR code encoding its SKU.\n\n• **View/Download**: Click the *QR* badge in the Products table row, or open the Edit modal\n• **Scan to transact**: On the Transactions page click *Scan QR* (inside the modal) or the *Scan In/Scan Out* header buttons\n• **Camera or Upload**: The scanner supports live camera AND uploading a photo of a QR code" },
  { p: /demo|test|seed|sample/i, a: "**Demo Data** — Load sample data via:\n```\ncurl -X POST http://localhost:8000/api/v1/dev/seed-demo\n```\nCreates 3 users, 6 products, and usage history.\n\nDemo logins:\n• admin@inventra.dev / **admin123**\n• store@inventra.dev / **store123**\n• viewer@inventra.dev / **viewer123**" },
  { p: /hello|hi|hey|start|what.*do|help/i, a: "Hi! I'm **Invy** 🤖, your Inventra assistant — powered by Gemini AI.\n\nI can help you with:\n• **Products** — add, edit, QR codes\n• **Transactions** — stock in/out, scan QR\n• **Forecasts** — charts, EWMA predictions\n• **Reorder** — recommendations, simulation\n• **Reports, Settings, Users, Audit Log**\n\nWhat would you like to know?" },
];

function localAnswer(q) {
  const entry = KB.find(e => e.p.test(q));
  return entry?.a ?? "I'm not sure about that. Try asking about:\n• Products or transactions\n• Forecasts or reorder\n• Reports, settings, or user roles\n• The audit log or dashboard";
}

// ── Gemini API call ──────────────────────────────────────────────────────────
async function askGemini(userMessage, history) {
  if (!GEMINI_KEY) throw new Error("No API key");

  const contents = [
    { role: "user", parts: [{ text: SYSTEM_PROMPT }] },
    { role: "model", parts: [{ text: "Understood! I'm Invy, ready to help with Inventra." }] },
    ...history.slice(-6).map(m => ({
      role: m.from === "user" ? "user" : "model",
      parts: [{ text: m.text }],
    })),
    { role: "user", parts: [{ text: userMessage }] },
  ];

  const res = await fetch(GEMINI_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents,
      generationConfig: { temperature: 0.7, maxOutputTokens: 512 },
    }),
  });

  if (!res.ok) throw new Error(`Gemini error ${res.status}`);
  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text ?? "Sorry, I couldn't generate a response.";
}

// ── Simple markdown renderer ──────────────────────────────────────────────────
function renderMd(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code style='background:var(--surface-3);padding:1px 5px;border-radius:3px;font-size:11px;font-family:monospace'>$1</code>")
    .replace(/\|(.+)\|/g, m => `<span style="display:inline-block;font-size:10.5px;background:var(--surface-3);padding:1px 4px;margin:1px;border-radius:3px">${m}</span>`)
    .replace(/\n/g, "<br/>");
}

const SUGGESTIONS = [
  "How do I add a product?",
  "What does Critical forecast mean?",
  "How do I scan QR to stock in?",
  "How do reports work?",
];

// ── Component ──────────────────────────────────────────────────────────────────
export default function Chatbot() {
  const [open, setOpen]       = useState(false);
  const [messages, setMessages] = useState([
    { from: "bot", text: `Hi! I'm **Invy** 🤖 — your Inventra assistant${GEMINI_KEY ? ", powered by **Gemini AI**" : ""}.\n\nAsk me anything about the app!` }
  ]);
  const [input, setInput]   = useState("");
  const [typing, setTyping] = useState(false);
  const bottomRef           = useRef(null);
  const inputRef            = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, typing]);
  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 200); }, [open]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q) return;
    const newMessages = [...messages, { from: "user", text: q }];
    setMessages(newMessages);
    setInput("");
    setTyping(true);
    try {
      let answer;
      if (GEMINI_KEY) {
        try {
          answer = await askGemini(q, messages);
        } catch {
          // Graceful fallback to local KB
          answer = localAnswer(q);
        }
      } else {
        await new Promise(r => setTimeout(r, 400 + Math.random() * 300));
        answer = localAnswer(q);
      }
      setMessages(m => [...m, { from: "bot", text: answer }]);
    } catch {
      setMessages(m => [...m, { from: "bot", text: "Something went wrong. Please try again." }]);
    } finally {
      setTyping(false);
    }
  }

  const showSuggestions = messages.length <= 1;

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
        onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.1)"; }}
        onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; }}
        title="Ask Invy"
      >
        {open ? <ChevronDown size={22} /> : <MessageCircle size={22} />}
      </button>

      {open && (
        <div style={{
          position: "fixed", bottom: 92, right: 28, zIndex: 300,
          width: 370, maxHeight: "78vh",
          background: "var(--surface)", border: "1px solid var(--line)",
          borderRadius: 20, display: "flex", flexDirection: "column",
          boxShadow: "0 20px 60px #00000080",
          animation: "slideUp 0.2s ease", overflow: "hidden",
        }}>
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "14px 18px",
            background: "linear-gradient(135deg, var(--purple), #7c6ced)",
          }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#ffffff25", display: "grid", placeItems: "center" }}>
              <Bot size={17} color="#fff" />
            </div>
            <div>
              <div style={{ font: "700 13px Manrope", color: "#fff", display: "flex", alignItems: "center", gap: 5 }}>
                Invy — Inventra Assistant
                {GEMINI_KEY && <Sparkles size={11} color="#d4d0ff" />}
              </div>
              <div style={{ fontSize: 10, color: "#d4d0ff" }}>
                {GEMINI_KEY ? "Powered by Gemini AI · Knows Inventra" : "Local KB · Add VITE_GEMINI_API_KEY to enable AI"}
              </div>
            </div>
            <button onClick={() => setOpen(false)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "#fff", opacity: 0.7 }}>
              <X size={16} />
            </button>
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
                  maxWidth: "83%", padding: "9px 13px",
                  borderRadius: m.from === "user" ? "14px 14px 4px 14px" : "4px 14px 14px 14px",
                  background: m.from === "user" ? "var(--purple)" : "var(--surface-3)",
                  color: m.from === "user" ? "#fff" : "var(--text)",
                  fontSize: 12, lineHeight: 1.65,
                  border: m.from === "bot" ? "1px solid var(--line)" : "none",
                }}
                  dangerouslySetInnerHTML={{ __html: renderMd(m.text) }}
                />
              </div>
            ))}

            {/* Typing */}
            {typing && (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--purple-glow)", border: "1px solid var(--purple)", display: "grid", placeItems: "center" }}>
                  <Bot size={13} color="var(--purple)" />
                </div>
                <div style={{ background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: "4px 14px 14px 14px", padding: "10px 14px", display: "flex", gap: 4 }}>
                  {[0,1,2].map(i => (
                    <div key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--purple)", animation: `bounce 1s ${i * 0.2}s infinite` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestion chips */}
          {showSuggestions && (
            <div style={{ padding: "0 14px 10px", display: "flex", flexWrap: "wrap", gap: 6 }}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => send(s)} style={{
                  fontSize: 10, padding: "5px 10px",
                  background: "var(--surface-3)", border: "1px solid var(--line)",
                  borderRadius: 99, color: "var(--text-2)", cursor: "pointer",
                  transition: "border-color 0.15s, color 0.15s",
                }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--purple)"; e.currentTarget.style.color = "var(--purple)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--line)"; e.currentTarget.style.color = "var(--text-2)"; }}
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
              placeholder={GEMINI_KEY ? "Ask Invy anything…" : "Ask about Inventra features…"}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !typing && send()}
            />
            <button className="btn btn-primary btn-icon" onClick={() => send()} disabled={!input.trim() || typing}>
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
        @keyframes slideUp {
          from { transform: translateY(16px); opacity: 0; }
          to   { transform: translateY(0);    opacity: 1; }
        }
      `}</style>
    </>
  );
}
