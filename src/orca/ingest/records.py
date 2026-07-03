"""Row fingerprints — the stable ID that makes incremental updates possible.

Each Excel row gets a short hash of its content. When a file is re-uploaded:
  - a row whose hash still exists  -> unchanged (reuse it, don't re-embed)
  - a hash that disappeared        -> the row was edited or deleted (drop it)
  - a hash that is new             -> the row was added (insert + embed it)

Hashing the CONTENT (not the position) means an edited row automatically looks
like "old row gone, new row arrived" — no fragile primary-key guessing needed.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any


def _canonical(value: Any) -> Any:
    """Turn a cell value into a stable, JSON-friendly form for hashing."""
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)          # 41.0 and 41 should hash the same
    return value


def row_fingerprint(sheet_name: str, row: dict[str, Any]) -> str:
    """A short, stable hash of one row's content (same content -> same hash)."""
    items = sorted((str(k), _canonical(v)) for k, v in row.items())
    payload = sheet_name + "|" + json.dumps(items, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# STAGE 6 - build the searchable text chunks (the "meaning" side)
# =============================================================================
def _fmt(value: Any) -> str:
    """Render a cell value for the chunk text (dates as plain YYYY-MM-DD)."""
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    return str(value)


def build_chunks(extract, company_id: str, file_id: str) -> list[dict]:
    """Turn a workbook into vector chunks: one per data row + one per side block.

    Each chunk = a readable line of text + metadata that points HOME
    (company / file / sheet / Excel row / row_hash) for tenant filtering,
    incremental updates, and citations.
    """
    chunks: list[dict] = []
    for sheet in extract.sheets:
        agg = set(sheet.aggregate_rows)
        for i, row in enumerate(sheet.rows):
            parts = [f"{col}: {_fmt(v)}" for col, v in row.items() if v is not None]
            if not parts:
                continue
            chunks.append({
                "id": f"{company_id}:{file_id}:{sheet.sheet_name}:{sheet.source_rows[i]}",
                "text": f"[{sheet.sheet_name}] " + ", ".join(parts),
                "metadata": {
                    "company_id": company_id, "file_id": file_id,
                    "sheet": sheet.sheet_name, "source_row": sheet.source_rows[i],
                    "row_hash": row_fingerprint(sheet.sheet_name, row),
                    "is_total": i in agg,
                },
            })
        # side blocks (e.g. "Fast Calculation") — searchable context, not SQL data
        for aux in sheet.aux_blocks:
            chunks.append({
                "id": f"{company_id}:{file_id}:{sheet.sheet_name}:aux:{aux.start_row}",
                "text": f"[{sheet.sheet_name} — note] {aux.text}",
                "metadata": {
                    "company_id": company_id, "file_id": file_id,
                    "sheet": sheet.sheet_name, "source_row": aux.start_row,
                    "row_hash": "", "is_total": False, "is_aux": True,
                },
            })
    return chunks
