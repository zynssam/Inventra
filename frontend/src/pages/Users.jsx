// src/pages/Users.jsx
import { useEffect, useState } from "react";
import { Users as API } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Modal, RoleBadge, Badge, Empty, Confirm, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Plus, Edit2, Trash2 } from "lucide-react";

function UserForm({ initial = {}, onSave, onClose }) {
  const [form, setForm] = useState({
    full_name: "", email: "", password: "", role: "viewer", is_active: true, ...initial,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  async function handleSave() {
    setError(""); setLoading(true);
    try {
      const body = { ...form };
      if (!body.password && initial.id) delete body.password;
      await onSave(body);
      onClose();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal title={initial.id ? "Edit User" : "Add User"} onClose={onClose} wide>
      {error && <div className="error-msg">{error}</div>}
      <div className="input-row">
        <div className="field"><label>Full Name *</label><input className="input" value={form.full_name} onChange={set("full_name")} placeholder="Alex Morgan" required /></div>
        <div className="field"><label>Email *</label><input className="input" type="email" value={form.email} onChange={set("email")} placeholder="user@company.com" disabled={!!initial.id} required /></div>
      </div>
      <div className="input-row">
        <div className="field">
          <label>Role *</label>
          <select className="input" value={form.role} onChange={set("role")}>
            <option value="admin">Admin</option>
            <option value="store_manager">Store Manager</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
        <div className="field" style={{ display: "flex", alignItems: "flex-end", paddingBottom: 4 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={form.is_active} onChange={set("is_active")} /> Active account
          </label>
        </div>
      </div>
      <div className="field">
        <label>{initial.id ? "New Password (leave blank to keep)" : "Password *"}</label>
        <input className="input" type="password" value={form.password} onChange={set("password")} placeholder={initial.id ? "Leave blank to keep current" : "Min 8 characters"} required={!initial.id} />
      </div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={handleSave} disabled={loading}>{loading ? "Saving…" : "Save User"}</button>
      </div>
    </Modal>
  );
}

export default function Users() {
  const { user: currentUser } = useAuth();
  const toast = useToast();
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal]     = useState(null);
  const [confirm, setConfirm] = useState(null);

  const fetchAll = () => {
    setLoading(true);
    API.list().then(d => setItems(d.items ?? d)).catch(e => toast.error(e.message)).finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, []);

  const handleCreate = async (b) => { await API.create(b); toast.success("User created"); fetchAll(); };
  const handleUpdate = async (id, b) => { await API.update(id, b); toast.success("User updated"); fetchAll(); };
  const handleDelete = async (id) => { await API.delete(id); toast.success("User deleted"); fetchAll(); };

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="User Management" subtitle={`${items.length} accounts`}>
        <button className="btn btn-primary" onClick={() => setModal("create")}><Plus size={15} /> Add User</button>
      </PageHeader>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan="6"><Empty icon="👤" message="No users yet" /></td></tr>
              ) : items.map(u => (
                <tr key={u.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div className="avatar" style={{ width: 28, height: 28, fontSize: 11 }}>
                        {(u.full_name ?? "U").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase()}
                      </div>
                      <span style={{ fontWeight: 600 }}>{u.full_name}</span>
                      {u.id === currentUser?.user_id && <span style={{ fontSize: 10, color: "var(--purple)" }}>(you)</span>}
                    </div>
                  </td>
                  <td className="td-muted">{u.email}</td>
                  <td><RoleBadge role={u.role} /></td>
                  <td><Badge state={u.is_active ? "healthy" : "muted"} label={u.is_active ? "Active" : "Inactive"} /></td>
                  <td className="td-muted">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal(u)}><Edit2 size={13} /></button>
                      {u.id !== currentUser?.user_id && (
                        <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setConfirm(u.id)}><Trash2 size={13} /></button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {modal === "create" && <UserForm onSave={handleCreate} onClose={() => setModal(null)} />}
      {modal && modal !== "create" && <UserForm initial={modal} onSave={b => handleUpdate(modal.id, b)} onClose={() => setModal(null)} />}
      {confirm && <Confirm title="Delete User" message="Permanently delete this account?" danger onConfirm={() => handleDelete(confirm)} onClose={() => setConfirm(null)} />}
    </div>
  );
}
