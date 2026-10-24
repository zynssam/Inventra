// src/pages/Transactions.jsx
import { useEffect, useState, useCallback } from "react";
import { Transactions as API, Products } from "../api";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Modal, ToastContainer, Empty, Confirm } from "../components/ui";
import { useToast } from "../hooks/useToast";
import { Plus, RotateCcw, ArrowUp, ArrowDown, SlidersHorizontal } from "lucide-react";

function TxnModal({ type, products, onSave, onClose }) {
  const titles = { "stock-in": "Stock In", "stock-out": "Stock Out", adjust: "Adjust Quantity" };
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState(1);
  const [newQty, setNewQty] = useState(0);
  const [reason, setReason] = useState("");
  const [txnType, setTxnType] = useState(type === "stock-in" ? "stock_in" : type === "stock-out" ? "stock_out" : "adjustment");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const product = products.find(p => p.id === Number(productId));

  async function handleSave() {
    setError(""); setLoading(true);
    try {
      if (type === "stock-in")  await API.stockIn ({ product_id: Number(productId), quantity: Number(qty), type: txnType, reason });
      if (type === "stock-out") await API.stockOut({ product_id: Number(productId), quantity: Number(qty), type: txnType, reason });
      if (type === "adjust")    await API.adjustment({ product_id: Number(productId), new_quantity: Number(newQty), reason });
      onSave();
      onClose();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal title={titles[type]} onClose={onClose}>
      {error && <div className="error-msg">{error}</div>}
      <div className="field">
        <label>Product *</label>
        <select className="input" value={productId} onChange={e => setProductId(e.target.value)} required>
          <option value="">— Select product —</option>
          {products.map(p => <option key={p.id} value={p.id}>{p.name} ({p.sku}) — {p.current_quantity} in stock</option>)}
        </select>
      </div>
      {product && (
        <div style={{ background: "var(--surface-3)", borderRadius: 8, padding: "10px 14px", marginBottom: 14, fontSize: 12 }}>
          Current stock: <strong>{product.current_quantity}</strong> {product.unit} · Reorder at: <strong>{product.reorder_point}</strong>
        </div>
      )}
      {type !== "adjust" && (
        <div className="field">
          <label>Quantity *</label>
          <input className="input" type="number" min={1} value={qty} onChange={e => setQty(e.target.value)} />
        </div>
      )}
      {type === "adjust" && (
        <div className="field">
          <label>New Quantity *</label>
          <input className="input" type="number" min={0} value={newQty} onChange={e => setNewQty(e.target.value)} />
        </div>
      )}
      {(type === "stock-in") && (
        <div className="field">
          <label>Transaction Type</label>
          <select className="input" value={txnType} onChange={e => setTxnType(e.target.value)}>
            <option value="stock_in">Stock In</option>
            <option value="po_receipt">PO Receipt</option>
          </select>
        </div>
      )}
      {(type === "stock-out") && (
        <div className="field">
          <label>Transaction Type</label>
          <select className="input" value={txnType} onChange={e => setTxnType(e.target.value)}>
            <option value="stock_out">Stock Out</option>
            <option value="stocktake">Stocktake</option>
          </select>
        </div>
      )}
      <div className="field">
        <label>Reason</label>
        <input className="input" value={reason} onChange={e => setReason(e.target.value)} placeholder="Optional reason" />
      </div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={handleSave} disabled={loading || !productId}>{loading ? "Saving…" : "Confirm"}</button>
      </div>
    </Modal>
  );
}

function ReverseModal({ txnId, onSave, onClose }) {
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setError(""); setLoading(true);
    try { await API.reverse(txnId, reason); onSave(); onClose(); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal title="Reverse Transaction" subtitle="This will undo the stock movement with an opposing entry." onClose={onClose}>
      {error && <div className="error-msg">{error}</div>}
      <div className="field"><label>Reason</label><input className="input" value={reason} onChange={e => setReason(e.target.value)} placeholder="Optional reason for reversal" /></div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn-danger" onClick={handleSave} disabled={loading}>{loading ? "Reversing…" : "Reverse"}</button>
      </div>
    </Modal>
  );
}

const TXN_COLOR = { stock_in: "#4ade80", po_receipt: "#4ade80", stock_out: "#f87171", stocktake: "#f87171", adjustment: "#fbbf24", reversal: "#8b5cf6" };

export default function Transactions() {
  const { canWrite, isAdmin } = useAuth();
  const toast = useToast();
  const [txns, setTxns]         = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [modal, setModal]       = useState(null);
  const [reversing, setReversing] = useState(null);
  const [page, setPage]         = useState(1);
  const [total, setTotal]       = useState(0);
  const [typeFilter, setTypeFilter] = useState("");

  const fetchTxns = useCallback(() => {
    setLoading(true);
    API.list({ page, page_size: 25, ...(typeFilter ? { txn_type: typeFilter } : {}) })
      .then(d => { setTxns(d.items ?? d); setTotal(d.total ?? d.length); })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [page, typeFilter]);

  useEffect(() => { fetchTxns(); }, [fetchTxns]);
  useEffect(() => {
    Products.list({ page_size: 200 }).then(d => setProducts(d.items ?? d)).catch(() => {});
  }, []);

  const onSaved = () => { toast.success("Done!"); fetchTxns(); };

  return (
    <div>
      <ToastContainer toasts={toast.toasts} remove={toast.remove} />
      <PageHeader title="Transactions" subtitle={`${total} total`}>
        {canWrite && <>
          <button className="btn btn-secondary btn-sm" onClick={() => setModal("stock-out")}><ArrowDown size={14} /> Stock Out</button>
          <button className="btn btn-primary" onClick={() => setModal("stock-in")}><ArrowUp size={14} /> Stock In</button>
        </>}
        {isAdmin && <button className="btn btn-secondary btn-sm" onClick={() => setModal("adjust")}><SlidersHorizontal size={14} /> Adjust</button>}
      </PageHeader>

      <div className="toolbar">
        <select className="input" style={{ width: "auto" }} value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }}>
          <option value="">All Types</option>
          {["stock_in","stock_out","adjustment","reversal","po_receipt","stocktake"].map(t => (
            <option key={t} value={t}>{t.replace("_", " ")}</option>
          ))}
        </select>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Product</th><th>Type</th><th>Qty Δ</th><th>Balance After</th><th>Reason</th><th>Date</th>{canWrite && <th></th>}</tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8" style={{ textAlign: "center", padding: 40 }}><div className="spinner" style={{ margin: "0 auto" }} /></td></tr>
              ) : txns.length === 0 ? (
                <tr><td colSpan="8"><Empty icon="📋" message="No transactions yet" /></td></tr>
              ) : txns.map(t => (
                <tr key={t.id}>
                  <td className="td-muted font-mono">#{t.id}</td>
                  <td style={{ fontWeight: 600 }}>{t.product_name ?? t.product_id}</td>
                  <td><span style={{ fontSize: 11, fontWeight: 600, color: TXN_COLOR[t.txn_type] ?? "var(--muted)" }}>{t.txn_type?.replace("_", " ")}</span></td>
                  <td><span className="quantity" style={{ color: t.quantity_delta >= 0 ? "#4ade80" : "#f87171" }}>{t.quantity_delta >= 0 ? "+" : ""}{t.quantity_delta}</span></td>
                  <td>{t.balance_after}</td>
                  <td className="td-muted">{t.reason ?? "—"}</td>
                  <td className="td-muted">{new Date(t.created_at).toLocaleDateString()}</td>
                  {canWrite && (
                    <td>
                      {!t.reverses_id && t.txn_type !== "reversal" && (
                        <button className="btn btn-ghost btn-icon btn-sm" title="Reverse" onClick={() => setReversing(t.id)}>
                          <RotateCcw size={13} />
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {total > 25 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button className="btn btn-secondary btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ lineHeight: "32px", fontSize: 12, color: "var(--muted)" }}>Page {page}</span>
          <button className="btn btn-secondary btn-sm" disabled={txns.length < 25} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}

      {(modal === "stock-in" || modal === "stock-out" || modal === "adjust") && (
        <TxnModal type={modal} products={products} onSave={onSaved} onClose={() => setModal(null)} />
      )}
      {reversing && <ReverseModal txnId={reversing} onSave={onSaved} onClose={() => setReversing(null)} />}
    </div>
  );
}
