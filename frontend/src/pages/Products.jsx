// src/pages/Products.jsx
import { useEffect, useState, useCallback } from "react";
import { Products as API, Categories, Suppliers } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Modal, StatusBadge, ForecastBadge, Empty, LoadingCenter, Confirm } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { ToastContainer } from "../components/ui";
import { Plus, Search, Edit2, Archive, RefreshCw } from "lucide-react";

function ProductForm({ initial = {}, categories = [], suppliers = [], onSave, onClose }) {
  const [form, setForm] = useState({
    name: "", sku: "", unit: "pcs", unit_cost: "", initial_quantity: 0,
    reorder_point: 0, min_order_qty: 1, category_id: "", supplier_id: "",
    ...initial,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  async function handleSave() {
    setError(""); setLoading(true);
    try {
      const body = {
        ...form,
        unit_cost: form.unit_cost,
        initial_quantity: Number(form.initial_quantity),
        reorder_point: Number(form.reorder_point),
        min_order_qty: Number(form.min_order_qty),
        category_id: form.category_id ? Number(form.category_id) : null,
        supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
      };
      await onSave(body);
      onClose();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal title={initial.id ? "Edit Product" : "Add Product"} onClose={onClose} wide>
      {error && <div className="error-msg">{error}</div>}
      <div className="input-row">
        <div className="field"><label>Name *</label><input className="input" value={form.name} onChange={set("name")} placeholder="Product name" required /></div>
        <div className="field"><label>SKU *</label><input className="input" value={form.sku} onChange={set("sku")} placeholder="SKU-001" disabled={!!initial.id} /></div>
      </div>
      <div className="input-row">
        <div className="field"><label>Unit</label><input className="input" value={form.unit} onChange={set("unit")} placeholder="pcs, kg, box…" /></div>
        <div className="field"><label>Unit Cost ($) *</label><input className="input" type="number" step="0.01" value={form.unit_cost} onChange={set("unit_cost")} /></div>
      </div>
      <div className="input-row">
        <div className="field"><label>Category</label>
          <select className="input" value={form.category_id ?? ""} onChange={set("category_id")}>
            <option value="">— None —</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div className="field"><label>Supplier</label>
          <select className="input" value={form.supplier_id ?? ""} onChange={set("supplier_id")}>
            <option value="">— None —</option>
            {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>
      {!initial.id && (
        <div className="field"><label>Initial Quantity</label><input className="input" type="number" value={form.initial_quantity} onChange={set("initial_quantity")} /></div>
      )}
      <div className="input-row">
        <div className="field"><label>Reorder Point</label><input className="input" type="number" value={form.reorder_point} onChange={set("reorder_point")} /></div>
        <div className="field"><label>Min Order Qty</label><input className="input" type="number" value={form.min_order_qty} onChange={set("min_order_qty")} /></div>
      </div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={handleSave} disabled={loading}>{loading ? "Saving…" : "Save Product"}</button>
      </div>
    </Modal>
  );
}

export default function Products() {
  const { canWrite, isAdmin } = useAuth();
  const toast = useToast();
  const [products, setProducts]   = useState([]);
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal]         = useState(null); // null | "create" | {product}
  const [confirm, setConfirm]     = useState(null);
  const [page, setPage]           = useState(1);
  const [total, setTotal]         = useState(0);

  const fetchProducts = useCallback(() => {
    setLoading(true);
    API.list({ search, status: statusFilter, page, page_size: 20 })
      .then(d => { setProducts(d.items ?? d); setTotal(d.total ?? d.length); })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [search, statusFilter, page]);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);
  useEffect(() => {
    Categories.list().then(d => setCategories(d.items ?? d)).catch(() => {});
    Suppliers.list().then(d => setSuppliers(d.items ?? d)).catch(() => {});
  }, []);

  async function handleCreate(body) {
    await API.create(body);
    toast.success("Product created");
    fetchProducts();
  }
  async function handleUpdate(id, body) {
    await API.update(id, body);
    toast.success("Product updated");
    fetchProducts();
  }
  async function handleArchive(id) {
    await API.archive(id);
    toast.success("Product archived");
    fetchProducts();
  }

  const fmtCurrency = v => `$${Number(v).toFixed(2)}`;
  const statusColor = s => s === "healthy" ? "#4ade80" : s === "low_stock" ? "#fbbf24" : "#f87171";

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Products" subtitle={`${total} products total`}>
        {canWrite && <button className="btn btn-primary" onClick={() => setModal("create")}><Plus size={15} /> Add Product</button>}
      </PageHeader>

      <div className="toolbar">
        <div className="toolbar-left">
          <div className="search-wrap">
            <Search size={14} />
            <input className="input" placeholder="Search name or SKU…" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} style={{ minWidth: 220 }} />
          </div>
          <select className="input" style={{ width: "auto" }} value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
            <option value="">All Status</option>
            <option value="healthy">Healthy</option>
            <option value="low_stock">Low Stock</option>
            <option value="out_of_stock">Out of Stock</option>
          </select>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchProducts}><RefreshCw size={13} /></button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Product</th><th>SKU</th><th>Stock</th><th>Reorder At</th><th>Unit Cost</th><th>Status</th><th>Forecast</th>{canWrite && <th></th>}</tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : products.length === 0 ? (
                <tr><td colSpan="8"><Empty message="No products found" /></td></tr>
              ) : products.map(p => (
                <tr key={p.id}>
                  <td><div style={{ fontWeight: 600 }}>{p.name}</div><div className="td-muted">{p.unit}</div></td>
                  <td className="font-mono">{p.sku}</td>
                  <td><span className="quantity" style={{ color: statusColor(p.status) }}>{p.current_quantity}</span></td>
                  <td className="td-muted">{p.reorder_point}</td>
                  <td>{fmtCurrency(p.unit_cost)}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td><ForecastBadge state={p.forecast_state} /></td>
                  {canWrite && (
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn btn-ghost btn-icon btn-sm" title="Edit" onClick={() => setModal(p)}><Edit2 size={13} /></button>
                        {isAdmin && <button className="btn btn-ghost btn-icon btn-sm" title="Archive" onClick={() => setConfirm(p.id)}><Archive size={13} /></button>}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button className="btn btn-secondary btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ lineHeight: "32px", fontSize: 12, color: "var(--muted)" }}>Page {page}</span>
          <button className="btn btn-secondary btn-sm" disabled={products.length < 20} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}

      {modal === "create" && (
        <ProductForm categories={categories} suppliers={suppliers} onSave={handleCreate} onClose={() => setModal(null)} />
      )}
      {modal && modal !== "create" && (
        <ProductForm initial={modal} categories={categories} suppliers={suppliers}
          onSave={b => handleUpdate(modal.id, b)} onClose={() => setModal(null)} />
      )}
      {confirm && (
        <Confirm title="Archive Product" message="This product will be archived and hidden from active inventory." danger
          onConfirm={() => handleArchive(confirm)} onClose={() => setConfirm(null)} />
      )}
    </div>
  );
}
