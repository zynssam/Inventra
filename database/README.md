# StockSense database

The database code, schema, migrations, and SQL scripts are in this folder. Run
Python modules from the repository root so imports use the `database` package.

## PostgreSQL

For a local PostgreSQL installation, start the PostgreSQL service and connect with
the `stocksense` role to the `stocksense` database. Verify the connection with:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U stocksense -d stocksense -c "\dt"
```

Docker is optional. If installed, run `docker compose up -d` from this folder.

## Python environment

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install sqlalchemy psycopg2-binary alembic python-dotenv
```

Set the database URL for the current PowerShell session, using your local password:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://stocksense:<password>@localhost:5432/stocksense"
```

Do not commit or share the real password.

## Alembic

Run Alembic from the backend project directory, if present:

```text
alembic init alembic
```

Configure `alembic.ini` with the database URL and set `target_metadata` in
`alembic/env.py` to `database.models.Base.metadata`. Generate and apply migrations
with `alembic revision --autogenerate -m "initial schema"` and `alembic upgrade head`.
Only the database schema owner should create Alembic migrations.

The ledger is append-only: the trigger rejects updates and deletes from
`stock_transactions`. `database/alembic_trigger_migration.py` contains the trigger
migration, and `ledger_trigger.sql` contains the SQL implementation.

## Seed demo data

`py -m database.seed_demo` loads the demo dataset, but **truncates existing data**.
Do not run it if the database contains data you need. The demo password hash in
`seed_demo.py` must also be replaced with a valid hash before seeding.

## CRUD operations

`database/crud.py` provides create, read, update, and delete helpers for products,
categories, and suppliers. Pass an SQLAlchemy `Session` to each function. Helpers
flush changes but do not commit; the caller controls the transaction:

```python
from decimal import Decimal
from sqlalchemy.orm import Session

from database.crud import (
    create_category,
    create_product,
    create_supplier,
    delete_product,
    get_product,
    list_products,
    update_product,
)

with Session(engine) as db, db.begin():
    category = create_category(db, name="Hardware")
    supplier = create_supplier(db, name="Acme Supplies")
    product = create_product(
        db,
        sku="WID-007",
        name="Hex Bolts",
        category_id=category.id,
        supplier_id=supplier.id,
        unit_cost=Decimal("0.40"),
        reorder_point=30,
    )
    update_product(db, product.id, name="Steel Hex Bolts")
    products = list_products(db)
    current = get_product(db, product.id)
    delete_product(db, product.id)
```

`update_category`, `update_supplier`, and `update_product` accept changed fields as
keyword arguments and return `None` if the ID does not exist. Their corresponding
`get_*` helpers also return `None` for missing IDs. `list_products` and
`list_suppliers` hide inactive records by default; pass `include_inactive=True` to
include them.

Product deletion is a soft delete (`is_active=False`) so transaction history remains
available. Product stock cannot be changed through CRUD helpers; use the stock
movement workflow to record stock changes. Deleting a category or supplier that is
still referenced raises `ValueError`.
