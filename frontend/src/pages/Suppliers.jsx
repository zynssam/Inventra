// src/pages/Suppliers.jsx
import { useEffect, useState } from "react";
import { Suppliers as API } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Modal, Empty, Confirm, Badge, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Plus, Edit2, Trash2 } from "lucide-react";

function SupplierForm({ initial = {}, onSave, onClose }) {
  const [form, setForm] = useState({
    name: "", contact_email: "", phone: "", lead_time_days: 7, is_active: true, ...initial,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  async function handleSave() {
    setError(""); setLoading(true);
    try { await onSave({ ...form, lead_time_days: Number(form.lead_time_days) }); onClose(); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal title={initial.id ? "Edit Supplier" : "Add Supplier"} onClose={onClose} wide>
      {error && <div className="error-msg">{error}</div>}
      <div className="field"><label>Name *</label><input className="input" value={form.name} onChange={set("name")} placeholder="Supplier name" required /></div>
      <div className="input-row">
        <div className="field"><label>Contact Email</label><input className="input" type="email" value={form.contact_email ?? ""} onChange={set("contact_email")} placeholder="orders@supplier.com" /></div>
        <div className="field"><label>Phone</label><input className="input" value={form.phone ?? ""} onChange={set("phone")} placeholder="+1 555 0100" /></div>
      </div>
      <div className="input-row">
        <div className="field"><label>Lead Time (days)</label><input className="input" type="number" min={0} value={form.lead_time_days} onChange={set("lead_time_days")} /></div>
        <div className="field" style={{ display: "flex", alignItems: "flex-end", paddingBottom: 4 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={form.is_active} onChange={set("is_active")} />
            Active supplier
          </label>
        </div>
      </div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={handleSave} disabled={loading || !form.name}>{loading ? "Saving…" : "Save"}</button>
      </div>
    </Modal>
  );
}

export default function Suppliers() {
  const { canWrite, isAdmin } = useAuth();
  const toast = useToast();
  const [items, setItems]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [modal, setModal]       = useState(null);
  const [confirm, setConfirm]   = useState(null);

  const fetchAll = () => {
    setLoading(true);
    API.list().then(d => setItems(d.items ?? d)).catch(e => toast.error(e.message)).finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, []);

  const handleCreate = async (b) => { await API.create(b); toast.success("Supplier added"); fetchAll(); };
  const handleUpdate = async (id, b) => { await API.update(id, b); toast.success("Supplier updated"); fetchAll(); };
  const handleDelete = async (id) => { await API.delete(id); toast.success("Supplier deleted"); fetchAll(); };

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Suppliers" subtitle={`${items.length} suppliers`}>
        {canWrite && <button className="btn btn-primary" onClick={() => setModal("create")}><Plus size={15} /> Add Supplier</button>}
      </PageHeader>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Lead Time</th><th>Status</th>{canWrite && <th></th>}</tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan="6"><Empty icon="🚚" message="No suppliers yet" /></td></tr>
              ) : items.map(s => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td className="td-muted">{s.contact_email ?? "—"}</td>
                  <td className="td-muted">{s.phone ?? "—"}</td>
                  <td className="td-muted">{s.lead_time_days ?? 0}d</td>
                  <td><Badge state={s.is_active ? "healthy" : "muted"} label={s.is_active ? "Active" : "Inactive"} /></td>
                  {canWrite && (
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal(s)}><Edit2 size={13} /></button>
                        {isAdmin && <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setConfirm(s.id)}><Trash2 size={13} /></button>}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {modal === "create" && <SupplierForm onSave={handleCreate} onClose={() => setModal(null)} />}
      {modal && modal !== "create" && <SupplierForm initial={modal} onSave={b => handleUpdate(modal.id, b)} onClose={() => setModal(null)} />}
      {confirm && <Confirm title="Delete Supplier" message="Remove this supplier? This cannot be undone." danger onConfirm={() => handleDelete(confirm)} onClose={() => setConfirm(null)} />}
    </div>
  );
}
