"""
app/database.py — shim that re-exports Member A's database helpers.

⚠️  When Member A delivers the real database.py, REPLACE the single import
    line below with the real implementation. Delete app/_temp/database_temp.py too.
"""
# ONE import line — swap this when Member A delivers
from app._temp.database_temp import (  # noqa: F401
    engine,
    SessionLocal,
    get_db,
    create_tables,
)

from app._temp.models_temp import Base  # noqa: F401
