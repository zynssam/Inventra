"""
app/queries/usage.py — shim for Member A's usage query module.

⚠️  When Member A delivers app/queries/usage.py with real SQL,
    replace the import below. Delete app/_temp/queries_stub.py too.
"""
from app._temp.queries_stub import (  # noqa: F401
    UsageStats,
    get_usage,
    get_daily_series,
    get_incoming_stock,
)
