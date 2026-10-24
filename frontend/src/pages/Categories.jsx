// src/pages/Categories.jsx
import { useEffect, useState } from "react";
import { Categories as API } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Modal, Empty, Confirm, ToastContainer } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Plus, Edit2, Trash2 } from "lucide-react";

function CatForm({ initial = {}, onSave, onClose }) {
  const [name, setName] = useState(initial.name ?? "");
  const [description, setDescription] = useState(initial.description ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setError(""); setLoading(true);
    try { await onSave({ name, description }); onClose(); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal title={initial.id ? "Edit Category" : "Add Category"} onClose={onClose}>
      {error && <div className="error-msg">{error}</div>}
      <div className="field"><label>Name *</label><input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Category name" required /></div>
      <div className="field"><label>Description</label><input className="input" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" /></div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={handleSave} disabled={loading || !name}>{loading ? "Saving…" : "Save"}</button>
      </div>
    </Modal>
  );
}

export default function Categories() {
  const { canWrite, isAdmin } = useAuth();
  const toast = useToast();
  const [items, setItems]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal]   = useState(null);
  const [confirm, setConfirm] = useState(null);

  const fetchAll = () => {
    setLoading(true);
    API.list().then(d => setItems(d.items ?? d)).catch(e => toast.error(e.message)).finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, []);

  const handleCreate = async (b) => { await API.create(b); toast.success("Category created"); fetchAll(); };
  const handleUpdate = async (id, b) => { await API.update(id, b); toast.success("Category updated"); fetchAll(); };
  const handleDelete = async (id) => { await API.delete(id); toast.success("Category deleted"); fetchAll(); };

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Categories" subtitle={`${items.length} categories`}>
        {canWrite && <button className="btn btn-primary" onClick={() => setModal("create")}><Plus size={15} /> Add Category</button>}
      </PageHeader>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Description</th>{canWrite && <th></th>}</tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="3" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan="3"><Empty icon="🏷️" message="No categories yet" /></td></tr>
              ) : items.map(c => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 600 }}>{c.name}</td>
                  <td className="td-muted">{c.description ?? "—"}</td>
                  {canWrite && (
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal(c)}><Edit2 size={13} /></button>
                        {isAdmin && <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setConfirm(c.id)}><Trash2 size={13} /></button>}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {modal === "create" && <CatForm onSave={handleCreate} onClose={() => setModal(null)} />}
      {modal && modal !== "create" && <CatForm initial={modal} onSave={b => handleUpdate(modal.id, b)} onClose={() => setModal(null)} />}
      {confirm && <Confirm title="Delete Category" message="Are you sure? This cannot be undone." danger onConfirm={() => handleDelete(confirm)} onClose={() => setConfirm(null)} />}
    </div>
  );
}
