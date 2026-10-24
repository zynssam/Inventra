from sqlalchemy import text


def stock_movements(db, filters) -> list[dict]:
    """filters: object/dict with optional product_id, txn_type, date_from, date_to."""
    f = filters if isinstance(filters, dict) else vars(filters)
    sql = text("""
    SELECT t.id, t.created_at, p.sku, p.name, t.txn_type, t.quantity_delta,
           t.balance_after, t.reason, u.email AS user_email
    FROM stock_transactions t JOIN products p ON p.id = t.product_id
    LEFT JOIN users u ON u.id = t.created_by
    WHERE (CAST(:pid AS int)  IS NULL OR t.product_id = :pid)
      AND (CAST(:typ AS text) IS NULL OR t.txn_type   = :typ)
      AND (CAST(:df  AS date) IS NULL OR t.created_at::date >= :df)
      AND (CAST(:dt  AS date) IS NULL OR t.created_at::date <= :dt)
    ORDER BY t.created_at DESC, t.id DESC""")
    return [dict(r._mapping) for r in db.execute(sql, {
        "pid": f.get("product_id"), "typ": f.get("txn_type"),
        "df": f.get("date_from"), "dt": f.get("date_to")})]


def inventory_valuation(db) -> list[dict]:
    sql = text("""SELECT sku, name, current_quantity, unit_cost,
                         current_quantity * unit_cost AS total_value
                  FROM products WHERE is_active ORDER BY total_value DESC""")
    return [dict(r._mapping) for r in db.execute(sql)]


def stock_status(db) -> list[dict]:
    sql = text("""SELECT sku, name, current_quantity, reorder_point,
                  CASE WHEN current_quantity = 0 THEN 'out_of_stock'
                       WHEN current_quantity <= reorder_point THEN 'low_stock'
                       ELSE 'healthy' END AS status
                  FROM products WHERE is_active ORDER BY current_quantity""")
    return [dict(r._mapping) for r in db.execute(sql)]


def supplier_purchases(db, date_from, date_to) -> list[dict]:
    sql = text("""
    SELECT s.name AS supplier, COUNT(DISTINCT po.id) AS orders,
           SUM(i.quantity_received * i.unit_cost) AS received_value
    FROM purchase_orders po JOIN suppliers s ON s.id = po.supplier_id
    JOIN purchase_order_items i ON i.purchase_order_id = po.id
    WHERE po.status <> 'cancelled'
      AND (CAST(:df AS date) IS NULL OR po.created_at::date >= :df)
      AND (CAST(:dt AS date) IS NULL OR po.created_at::date <= :dt)
    GROUP BY s.name ORDER BY received_value DESC""")
    return [dict(r._mapping) for r in db.execute(sql, {"df": date_from, "dt": date_to})]
