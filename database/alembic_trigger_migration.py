"""Second migration: ledger trigger. Copy into backend/alembic/versions/ after
running `alembic revision --autogenerate -m "initial schema"`, and set down_revision
to the id of that initial revision."""
from pathlib import Path
from alembic import op

revision = "0002_ledger_trigger"
down_revision = "REPLACE_WITH_INITIAL_REVISION_ID"
branch_labels = None
depends_on = None

SQL = (Path(__file__).resolve().parents[3] / "db" / "ledger_trigger.sql").read_text()

def upgrade():
    op.execute(SQL)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_ledger_immutable ON stock_transactions")
    op.execute("DROP FUNCTION IF EXISTS forbid_ledger_change()")
