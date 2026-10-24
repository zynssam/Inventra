from sqlalchemy import text


def summary(db) -> dict:
    r = db.execute(text("""
      SELECT COUNT(*) FILTER (WHERE is_active)                                   AS total_products,
             COALESCE(SUM(current_quantity * unit_cost) FILTER (WHERE is_active),0) AS inventory_value,
             COUNT(*) FILTER (WHERE is_active AND current_quantity = 0)          AS out_of_stock,
             COUNT(*) FILTER (WHERE is_active AND current_quantity > 0
                                AND current_quantity <= reorder_point)           AS low_stock
      FROM products""")).one()
    return dict(r._mapping)


def movement_chart(db, days: int) -> list[dict]:
    sql = text("""
    SELECT d::date AS date,
           COALESCE(SUM(t.quantity_delta) FILTER (WHERE t.quantity_delta > 0), 0)  AS stock_in,
           COALESCE(-SUM(t.quantity_delta) FILTER (WHERE t.quantity_delta < 0), 0) AS stock_out
    FROM generate_series(CURRENT_DATE - CAST(:days AS int) + 1, CURRENT_DATE, interval '1 day') d
    LEFT JOIN stock_transactions t ON t.created_at::date = d::date
    GROUP BY d ORDER BY d""")
    return [dict(r._mapping) for r in db.execute(sql, {"days": days})]


def top_used(db, days: int, limit: int) -> list[dict]:
    sql = text("""
    SELECT p.id AS product_id, p.sku, p.name, SUM(-t.quantity_delta) AS used
    FROM stock_transactions t JOIN products p ON p.id = t.product_id
    WHERE t.txn_type='stock_out' AND t.created_at >= now() - make_interval(days => CAST(:days AS int))
      AND NOT EXISTS (SELECT 1 FROM stock_transactions r WHERE r.reverses_id = t.id)
    GROUP BY p.id ORDER BY used DESC LIMIT :limit""")
    return [dict(r._mapping) for r in db.execute(sql, {"days": days, "limit": limit})]


def category_value(db) -> list[dict]:
    sql = text("""
    SELECT COALESCE(c.name,'Uncategorised') AS category,
           SUM(p.current_quantity * p.unit_cost) AS value
    FROM products p LEFT JOIN categories c ON c.id = p.category_id
    WHERE p.is_active GROUP BY 1 ORDER BY value DESC""")
    return [dict(r._mapping) for r in db.execute(sql)]


def alerts_base(db) -> list[dict]:
    sql = text("""
    SELECT id AS product_id, sku, name, current_quantity, reorder_point,
           CASE WHEN current_quantity = 0 THEN 'out_of_stock' ELSE 'low_stock' END AS alert
    FROM products WHERE is_active AND current_quantity <= reorder_point
    ORDER BY current_quantity""")
    return [dict(r._mapping) for r in db.execute(sql)]
