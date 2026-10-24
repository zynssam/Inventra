from sqlalchemy import text


def reconciliation(db) -> list[dict]:
    """Rows where cached products.current_quantity != sum of ledger. Must be EMPTY."""
    sql = text("""
    SELECT p.id AS product_id, p.sku, p.current_quantity AS cached_qty,
           COALESCE(SUM(t.quantity_delta), 0) AS ledger_qty
    FROM products p LEFT JOIN stock_transactions t ON t.product_id = p.id
    GROUP BY p.id HAVING p.current_quantity <> COALESCE(SUM(t.quantity_delta), 0)
    """)
    return [dict(r._mapping) for r in db.execute(sql)]


def dead_stock(db, days: int) -> list[dict]:
    sql = text("""
    SELECT p.id AS product_id, p.sku, p.name, p.current_quantity,
           p.current_quantity * p.unit_cost AS value_tied_up
    FROM products p
    WHERE p.is_active AND p.current_quantity > 0 AND NOT EXISTS (
      SELECT 1 FROM stock_transactions t
      WHERE t.product_id = p.id AND t.txn_type = 'stock_out'
        AND t.created_at >= now() - make_interval(days => CAST(:days AS int)))
    ORDER BY value_tied_up DESC
    """)
    return [dict(r._mapping) for r in db.execute(sql, {"days": days})]


def abc_classification(db) -> list[dict]:
    sql = text("""
    WITH v AS (
      SELECT p.id AS product_id, p.sku, p.name,
             COALESCE(SUM(-t.quantity_delta),0) * p.unit_cost AS consumption_value
      FROM products p LEFT JOIN stock_transactions t
        ON t.product_id = p.id AND t.txn_type='stock_out' AND t.created_at >= now() - interval '90 days'
      GROUP BY p.id),
    c AS (SELECT *, SUM(consumption_value) OVER (ORDER BY consumption_value DESC) /
                    NULLIF(SUM(consumption_value) OVER (), 0) AS cum_share FROM v)
    SELECT product_id, sku, name, consumption_value,
           CASE WHEN cum_share <= 0.8 THEN 'A' WHEN cum_share <= 0.95 THEN 'B' ELSE 'C' END AS abc_class
    FROM c ORDER BY consumption_value DESC
    """)
    return [dict(r._mapping) for r in db.execute(sql)]


def usage_outliers(db, window_days: int) -> list[dict]:
    """Days where a product's usage > mean + 2*stddev of its own daily usage."""
    sql = text("""
    WITH daily AS (
      SELECT product_id, created_at::date AS d, SUM(-quantity_delta) AS qty
      FROM stock_transactions
      WHERE txn_type='stock_out' AND created_at >= now() - make_interval(days => CAST(:w AS int))
      GROUP BY 1,2),
    s AS (SELECT *, AVG(qty) OVER (PARTITION BY product_id) AS mu,
                    STDDEV_POP(qty) OVER (PARTITION BY product_id) AS sd FROM daily)
    SELECT product_id, d AS date, qty, ROUND(mu,2) AS mean_qty FROM s WHERE sd > 0 AND qty > mu + 2*sd
    """)
    return [dict(r._mapping) for r in db.execute(sql, {"w": window_days})]
