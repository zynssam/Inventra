"""
app/services/reporting_service.py — CSV/JSON report builders.

CSV rules (architecture.md §8.13):
- UTF-8 with BOM
- Cells starting with = + - @ are prefixed with a single-quote to prevent
  formula injection in spreadsheets.

Public API:
  build_csv(headers, rows) -> bytes
"""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any


_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _escape_cell(value: Any) -> str:
    """Prefix formula-injection characters with a single-quote."""
    s = str(value) if value is not None else ""
    if s and s[0] in _FORMULA_PREFIXES:
        return "'" + s
    return s


def build_csv(headers: list[str], rows: list[list[Any]]) -> bytes:
    """
    Build a UTF-8-BOM CSV from headers and rows.
    Returns bytes suitable for a StreamingResponse body.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_escape_cell(cell) for cell in row])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def csv_filename(report_name: str) -> str:
    """Return filename like stock-movements_2026-10-24.csv"""
    return f"{report_name}_{date.today().isoformat()}.csv"
