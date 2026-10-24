// src/pages/Settings.jsx
import { useEffect, useState } from "react";
import { Settings as API } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHeader, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Save } from "lucide-react";

// Backend returns a flat SettingsOut object with these exact keys
const FIELDS = [
  { key: "usage_window_days",   label: "Usage Window (days)",        desc: "Past days analysed for average daily usage",           min: 7,  max: 365 },
  { key: "warning_days",        label: "Warning Threshold (days)",   desc: "Days until stockout that triggers a Warning state",    min: 1,  max: 90  },
  { key: "critical_days",       label: "Critical Threshold (days)",  desc: "Days until stockout that triggers a Critical state",   min: 1,  max: 30  },
  { key: "min_usage_days",      label: "Min Usage Days",             desc: "Minimum data days needed before a forecast is made",   min: 1,  max: 30  },
  { key: "default_target_days", label: "Default Target Days",        desc: "Default days of stock to target when recommending",    min: 7,  max: 180 },
];

export default function Settings() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const [form, setForm]     = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);

  useEffect(() => {
    // Backend returns flat object: { usage_window_days: 30, warning_days: 14, ... }
    API.get()
      .then(data => setForm(data))
      .catch(e => toast.error("Failed to load settings: " + e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      // PUT /settings accepts SettingsUpdate (same flat shape, all optional)
      const body = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, Number(v)])
      );
      const updated = await API.update(body);
      setForm(updated);
      toast.success("Settings saved");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  }

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Settings" subtitle="Inventory forecast and reorder thresholds">
        {isAdmin && (
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={14} /> {saving ? "Saving…" : "Save Settings"}
          </button>
        )}
      </PageHeader>

      {loading ? (
        <div className="card"><div className="empty">Loading settings…</div></div>
      ) : (
        <div style={{ maxWidth: 640 }}>
          <div className="card">
            <div className="section-title">Forecast &amp; Reorder Parameters</div>
            {FIELDS.map(f => (
              <div key={f.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 0", borderBottom: "1px solid var(--line)" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{f.label}</div>
                  <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 3 }}>{f.desc}</div>
                </div>
                {isAdmin ? (
                  <input
                    className="input" type="number" min={f.min} max={f.max}
                    value={form[f.key] ?? ""}
                    onChange={set(f.key)}
                    style={{ width: 100, textAlign: "center" }}
                  />
                ) : (
                  <span style={{ font: "700 15px Manrope", color: "var(--purple)" }}>
                    {form[f.key] ?? "—"}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
