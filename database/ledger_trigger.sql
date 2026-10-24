-- Ledger protection: stock_transactions is append-only.
CREATE OR REPLACE FUNCTION forbid_ledger_change() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'stock_transactions is append-only (% blocked)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ledger_immutable ON stock_transactions;
CREATE TRIGGER trg_ledger_immutable
  BEFORE UPDATE OR DELETE ON stock_transactions
  FOR EACH ROW EXECUTE FUNCTION forbid_ledger_change();
-- NOTE: TRUNCATE is not blocked by row triggers, so the reset script still works.
