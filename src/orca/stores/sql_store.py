"""ORCA SQL store — the EXACT-numbers home.

One typed table per sheet, so the agent can ask real SQL questions (SUM, AVG,
MAX, filter by date...) and get exact answers — numbers never pass through the
LLM to be "read". SQLite now; the same shape moves to Postgres later.

Every row also carries the tenant + source identifiers we agreed on
(company_id, file_id, sheet, source_row, row_hash) so that:
  - multi-tenant isolation works (filter by company_id / file_id),
  - answers can cite their source (sheet + Excel row),
  - re-uploads can be handled incrementally later (via row_hash).

SECURITY: column/sheet names come from user files, so they are STRICTLY
sanitised before they ever touch a table/column name, and all VALUES are passed
as parameters (never string-formatted into SQL). No user text is concatenated
into a query.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from orca.ingest.excel_processor import SheetTable, WorkbookExtract
from orca.ingest.records import row_fingerprint

logger = logging.getLogger(__name__)

# Reserved metadata columns added to every sheet table (prefixed so they can't
# collide with a real spreadsheet column).
_META_COLUMNS = [
    ("_orca_company", "TEXT"),
    ("_orca_file", "TEXT"),
    ("_orca_sheet", "TEXT"),
    ("_orca_row", "INTEGER"),   # 1-based Excel row number (for citations)
    ("_orca_hash", "TEXT"),     # row fingerprint (for incremental updates)
    ("_orca_is_total", "INTEGER"),  # 1 = a Total/summary row (exclude from sums)
]


def _safe_ident(name: str, used: set[str]) -> str:
    """Turn any string into a safe, unique SQL identifier ([a-z0-9_], unique)."""
    s = re.sub(r"\W+", "_", str(name).strip().lower()).strip("_")
    if not s or not re.match(r"[a-z_]", s[0]):
        s = "c_" + s               # must not start with a digit
    s = s[:60]
    base, n = s, 1
    while s in used or s.startswith("_orca_"):
        n += 1
        s = f"{base}_{n}"
    used.add(s)
    return s


def _sqlite_type(data_type: str) -> str:
    """Map our measured column type to a SQLite column type."""
    if data_type == "number":
        return "REAL"
    return "TEXT"                   # dates stored as ISO text, everything else text


def _to_sql_value(value: Any) -> Any:
    """Convert a Python cell value to something SQLite stores well."""
    if isinstance(value, _dt.datetime):
        return value.isoformat()   # sortable, comparable ISO date string
    return value                   # int/float/str/None pass straight through


class SqlStore:
    """A thin wrapper over one SQLite database file."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_catalog()

    # -- catalog: the metadata registry of what's been ingested ---------------
    def _ensure_catalog(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orca_catalog (
                company_id  TEXT,
                file_id     TEXT,
                sheet       TEXT,
                table_name  TEXT,
                columns     TEXT,   -- JSON: original -> safe column names
                row_count   INTEGER,
                total_rows  INTEGER,
                ingested_at TEXT,
                PRIMARY KEY (company_id, file_id, sheet)
            )
            """
        )
        self._conn.commit()

    def _table_name(self, file_id: str, sheet: str) -> str:
        used: set[str] = set()
        return "t_" + _safe_ident(f"{file_id}_{sheet}", used)

    # -- writing --------------------------------------------------------------
    def store_workbook(self, company_id: str, file_id: str,
                       extract: WorkbookExtract) -> None:
        """Store every non-empty sheet of a workbook."""
        for sheet in extract.sheets:
            if sheet.n_rows == 0:
                continue
            self.store_sheet(company_id, file_id, sheet)
        self._conn.commit()

    def store_sheet(self, company_id: str, file_id: str, sheet: SheetTable) -> None:
        """Create (if needed) the sheet's table and WHOLESALE-replace this
        file's rows in it. SQL writes are cheap, so replace is simplest + always
        correct; the costly vector side is what we'll diff incrementally later."""
        table = self._table_name(file_id, sheet.sheet_name)

        # Map each original column -> a safe SQL column name + its SQLite type.
        used: set[str] = set()
        col_map: dict[str, str] = {}
        col_types: dict[str, str] = {}
        for orig in sheet.columns:
            safe = _safe_ident(orig, used)
            col_map[orig] = safe
            meta = sheet.column_meta.get(orig, {})
            col_types[safe] = _sqlite_type(meta.get("data_type", "text"))

        # CREATE TABLE with reserved metadata columns + the sheet's columns.
        col_defs = [f'"{c}" {t}' for c, t in _META_COLUMNS]
        col_defs += [f'"{safe}" {col_types[safe]}' for safe in col_map.values()]
        self._conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})')

        # Wholesale-replace: remove this company+file's existing rows first.
        self._conn.execute(
            f'DELETE FROM "{table}" WHERE _orca_company = ? AND _orca_file = ?',
            (company_id, file_id),
        )

        # Insert every row (values are ALL parameterised — no user text in SQL).
        meta_names = [c for c, _ in _META_COLUMNS]
        all_cols = meta_names + list(col_map.values())
        placeholders = ", ".join("?" for _ in all_cols)
        col_list = ", ".join(f'"{c}"' for c in all_cols)
        insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        agg = set(sheet.aggregate_rows)
        rows_to_insert = []
        for i, row in enumerate(sheet.rows):
            fingerprint = row_fingerprint(sheet.sheet_name, row)
            meta_vals = [
                company_id, file_id, sheet.sheet_name,
                sheet.source_rows[i], fingerprint, 1 if i in agg else 0,
            ]
            data_vals = [_to_sql_value(row[orig]) for orig in sheet.columns]
            rows_to_insert.append(meta_vals + data_vals)
        self._conn.executemany(insert_sql, rows_to_insert)

        # Update the catalog (metadata registry).
        self._conn.execute(
            """
            INSERT INTO orca_catalog
                (company_id, file_id, sheet, table_name, columns, row_count, total_rows, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id, file_id, sheet) DO UPDATE SET
                table_name=excluded.table_name, columns=excluded.columns,
                row_count=excluded.row_count, total_rows=excluded.total_rows,
                ingested_at=excluded.ingested_at
            """,
            (company_id, file_id, sheet.sheet_name, table, json.dumps(col_map),
             len(sheet.rows), len(agg), _dt.datetime.now().isoformat()),
        )
        logger.info("Stored %r -> table %r (%d rows, %d total-rows)",
                    sheet.sheet_name, table, len(sheet.rows), len(agg))

    # -- reading (read-only helper, for tests / the agent later) --------------
    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a read-only SELECT and return the rows."""
        return list(self._conn.execute(sql, params).fetchall())

    def catalog(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM orca_catalog ORDER BY sheet")

    def close(self) -> None:
        self._conn.close()
