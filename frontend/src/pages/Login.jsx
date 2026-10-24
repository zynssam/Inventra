// src/pages/Login.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const DEMOS = [
  { email: "admin@inventra.dev",  pass: "admin123",  role: "Admin · Full access" },
  { email: "store@inventra.dev",  pass: "store123",  role: "Store Manager · Daily ops" },
  { email: "viewer@inventra.dev", pass: "viewer123", role: "Viewer · Read-only" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showDemos, setShowDemos] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Incorrect email or password.");
    } finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "1fr 1fr" }}>
      {/* Left panel */}
      <div style={{
        background: "linear-gradient(145deg, #5548e8, #4439c7)",
        backgroundImage: "url('/inventra-login-bg.svg'), linear-gradient(145deg,#5548e8,#4439c7)",
        backgroundSize: "cover, cover",
        display: "flex", flexDirection: "column", padding: "48px 8%",
        position: "relative", overflow: "hidden", color: "#fff",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11, font: "800 18px Manrope", position: "relative", zIndex: 1 }}>
          <div style={{ width: 35, height: 35, borderRadius: 11, background: "#ffffff20", border: "1px solid #ffffff30", display: "grid", placeItems: "center" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 20 }}>
              <path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9M8 5.3l8 4.5"/>
            </svg>
          </div>
          Inventra
        </div>
        <div style={{ margin: "auto 0", maxWidth: 440, position: "relative", zIndex: 1 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "1.1px", color: "#d3d0ff", textTransform: "uppercase", marginBottom: 16 }}>
            Inventory, in focus
          </div>
          <h1 style={{ font: "700 clamp(36px,4vw,52px)/1.12 Manrope", margin: "0 0 16px", letterSpacing: -1.7 }}>
            Know what you have.<br />Know what you need.
          </h1>
          <p style={{ color: "#e4e2ff", fontSize: 14, lineHeight: 1.8, maxWidth: 360 }}>
            A clearer view of your stock, a calmer way to plan ahead. Keep every item moving in the right direction.
          </p>
          {/* Decorative bars */}
          <div style={{ marginTop: 36, width: "min(440px,100%)", height: 140, border: "1px solid #ffffff38", borderRadius: 16, background: "#ffffff0c", padding: 17, position: "relative" }}>
            <div style={{ fontSize: 10, color: "#dedcff", marginBottom: 8 }}>Stock health · This month</div>
            <div style={{ position: "absolute", bottom: 17, left: 18, right: 18, height: 80, display: "flex", alignItems: "end", gap: 9 }}>
              {[38,55,44,72,58,90,76].map((h,i) => (
                <div key={i} style={{ flex: 1, height: `${h}%`, background: "linear-gradient(0deg,#b2adff99,#fff)", borderRadius: "5px 5px 1px 1px", opacity: 0.85 }} />
              ))}
            </div>
          </div>
        </div>
        <div style={{ fontSize: 10, color: "#d4d1ff", position: "relative", zIndex: 1 }}>A little more clarity for every workday.</div>
      </div>

      {/* Right panel */}
      <div style={{ display: "grid", placeItems: "center", padding: 32, background: "var(--ink)" }}>
        <form style={{ width: "min(380px,100%)" }} onSubmit={handleSubmit}>
          <h2 style={{ font: "700 26px Manrope", marginBottom: 6, color: "var(--text)" }}>Welcome back</h2>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 28 }}>Sign in to your workspace to continue.</p>

          {error && <div className="error-msg">{error}</div>}

          <div className="field">
            <label>Email address</label>
            <input className="input" type="email" placeholder="you@company.com" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input className="input" type="password" placeholder="Enter your password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", padding: 13, marginBottom: 20, justifyContent: "center" }}>
            {loading ? "Signing in…" : "Sign in →"}
          </button>

          {/* Demo accounts */}
          <div style={{ borderTop: "1px solid var(--line)", paddingTop: 18 }}>
            <button type="button" className="btn btn-ghost" style={{ width: "100%", justifyContent: "space-between", fontSize: 12, padding: "4px 0" }}
              onClick={() => setShowDemos(v => !v)}>
              Try a demo account <span>{showDemos ? "▲" : "▼"}</span>
            </button>
            {showDemos && (
              <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                {DEMOS.map(d => (
                  <button key={d.email} type="button" style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 8, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", textAlign: "left", color: "var(--text)", transition: "border-color 0.15s" }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = "var(--purple)"}
                    onMouseLeave={e => e.currentTarget.style.borderColor = "var(--line)"}
                    onClick={() => { setEmail(d.email); setPassword(d.pass); setShowDemos(false); }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{d.email}</div>
                      <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 2 }}>{d.role}</div>
                    </div>
                    <span style={{ color: "var(--purple)", fontWeight: 700 }}>↗</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
