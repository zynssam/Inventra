"""Usage queries (owner: Member A). Raw numbers only; B applies business rules."""
from dataclasses import dataclass
from datetime import date, timedelta
from sqlalchemy import text


@dataclass
class UsageStats:
    total_usage: int
    usage_days: int
    first_activity_date: date | None
    recent_half_usage: int
    earlier_half_usage: int


# Usage = stock_out rows that were NOT reversed. Reversal rows are excluded too.
_USAGE_SQL = text("""
WITH bounds AS (
  SELECT CAST(:today AS date) - CAST(:window AS int) AS start_d,
         CAST(:today AS date) - CAST(:window AS int) / 2 AS mid_d
),
usage AS (
  SELECT t.product_id, t.created_at::date AS d, -t.quantity_delta AS qty
  FROM stock_transactions t, bounds b
  WHERE t.txn_type = 'stock_out'
    AND t.created_at::date >  b.start_d
    AND t.created_at::date <= CAST(:today AS date)
    AND NOT EXISTS (SELECT 1 FROM stock_transactions r WHERE r.reverses_id = t.id)
    AND (CAST(:ids AS int[]) IS NULL OR t.product_id = ANY(CAST(:ids AS int[])))
),
first_act AS (
  SELECT product_id, MIN(created_at)::date AS first_d
  FROM stock_transactions GROUP BY product_id
)
SELECT p.id AS product_id,
       COALESCE(SUM(u.qty), 0)                                   AS total_usage,
       COUNT(DISTINCT u.d)                                       AS usage_days,
       f.first_d                                                 AS first_activity_date,
       COALESCE(SUM(u.qty) FILTER (WHERE u.d >  (SELECT mid_d FROM bounds)), 0) AS recent_half,
       COALESCE(SUM(u.qty) FILTER (WHERE u.d <= (SELECT mid_d FROM bounds)), 0) AS earlier_half
FROM products p
LEFT JOIN usage u     ON u.product_id = p.id
LEFT JOIN first_act f ON f.product_id = p.id
WHERE p.is_active AND (CAST(:ids AS int[]) IS NULL OR p.id = ANY(CAST(:ids AS int[])))
GROUP BY p.id, f.first_d
""")


def get_usage(db, product_ids: list[int] | None, window_days: int, today: date) -> dict[int, UsageStats]:
    rows = db.execute(_USAGE_SQL, {"ids": product_ids, "window": window_days, "today": today})
    return {
        r.product_id: UsageStats(r.total_usage, r.usage_days, r.first_activity_date,
                                 r.recent_half, r.earlier_half)
        for r in rows
    }


def get_daily_series(db, product_id: int, days: int) -> list[dict]:
    sql = text("""
    SELECT d::date AS date,
           COALESCE(SUM(-t.quantity_delta) FILTER (WHERE t.txn_type='stock_out'
                    AND NOT EXISTS (SELECT 1 FROM stock_transactions r WHERE r.reverses_id=t.id)), 0) AS used,
           COALESCE(SUM(t.quantity_delta) FILTER (WHERE t.quantity_delta > 0
                    AND t.txn_type IN ('stock_in','po_receipt')), 0) AS received,
           (SELECT balance_after FROM stock_transactions x
             WHERE x.product_id = :pid AND x.created_at::date <= d::date
             ORDER BY x.created_at DESC, x.id DESC LIMIT 1) AS balance
    FROM generate_series(CURRENT_DATE - CAST(:days AS int) + 1, CURRENT_DATE, interval '1 day') d
    LEFT JOIN stock_transactions t
           ON t.product_id = :pid AND t.created_at::date = d::date
    GROUP BY d ORDER BY d
    """)
    return [dict(r._mapping) for r in db.execute(sql, {"pid": product_id, "days": days})]


def get_incoming_stock(db, product_ids: list[int] | None) -> dict[int, int]:
    sql = text("""
    SELECT i.product_id, SUM(i.quantity_ordered - i.quantity_received) AS incoming
    FROM purchase_order_items i JOIN purchase_orders po ON po.id = i.purchase_order_id
    WHERE po.status IN ('ordered','partially_received')
      AND (CAST(:ids AS int[]) IS NULL OR i.product_id = ANY(CAST(:ids AS int[])))
    GROUP BY i.product_id
    """)
    return {r.product_id: int(r.incoming) for r in db.execute(sql, {"ids": product_ids})}
