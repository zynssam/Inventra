# Query signatures (A <-> B). Frozen in Phase 0. See backend/app/queries/*.py for the current bodies.
usage.py:     get_usage(db, product_ids, window_days, today) -> dict[int, UsageStats]
              get_daily_series(db, product_id, days) -> list[dict]
              get_incoming_stock(db, product_ids) -> dict[int, int]
dashboard.py: summary(db), movement_chart(db, days), top_used(db, days, limit), category_value(db), alerts_base(db)
reports.py:   stock_movements(db, filters), inventory_valuation(db), stock_status(db), supplier_purchases(db, date_from, date_to)
insights.py:  usage_outliers(db, window_days), dead_stock(db, days), abc_classification(db), reconciliation(db)
