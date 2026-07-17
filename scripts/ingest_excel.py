"""Ingest one Excel file into ORCA's stores (SQL + vectors) — LEGACY FALLBACK.

>>> SINCE 2026-07-18 (Session 25) THIS IS NO LONGER THE DEFAULT EXCEL DOOR. <<<
The INGEST GATE (private/run_gate.py) is now the default: it surveys the
sheet's real structure, asks the uploader the clarifying questions, remembers
the answers on a reading card, and only then ingests. It matched this path's
eval score (15/15, twice) with cleaner data. Keep this script only as the
gate-less fallback (e.g. on a checkout without the private/ folder).

Re-runs the proven Session-2 pipeline. Re-running is safe: both stores
wholesale-replace this file's previous rows/chunks.

Usage:  python scripts/ingest_excel.py [path-to-xlsx]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orca.ingest.excel_processor import extract_workbook
from orca.stores.sql_store import SqlStore
from orca.stores.vector_store import VectorStore

COMPANY = "demo"
FILE_ID = "ob7ola"
SQL_PATH = "data/stores/orca.db"
CHROMA_PATH = "data/stores/chroma"


def main() -> None:
    excel_path = sys.argv[1] if len(sys.argv) > 1 else "data/OB7ola.xlsx"

    print(f"1) Extracting {excel_path} ...")
    extract = extract_workbook(excel_path)
    for sheet in extract.sheets:
        print(f"   sheet {sheet.sheet_name!r}: {sheet.n_rows} rows, "
              f"{len(sheet.columns)} columns, "
              f"{len(sheet.aggregate_rows)} total-row(s)")

    # data-quality report (stage 6): problems in the SOURCE file, stored as-is
    issues = [msg for sheet in extract.sheets for msg in sheet.quality_issues]
    if issues:
        print(f"\n   DATA-QUALITY REPORT — {len(issues)} issue(s) found in the file "
              f"(stored as-is, please fix in the source):")
        for msg in issues:
            print(f"   ! {msg}")
        print()

    print("2) Storing exact numbers in the SQL store ...")
    sql = SqlStore(SQL_PATH)
    sql.store_workbook(COMPANY, FILE_ID, extract)

    print("3) Storing meaning chunks in the vector store ...")
    vectors = VectorStore(path=CHROMA_PATH)
    n = vectors.store_workbook(COMPANY, FILE_ID, extract)
    print(f"   {n} chunk(s) embedded")

    # 4) PROOF: for every number column, SUM of the data rows must equal the
    #    figure the sheet itself printed on its Total row.
    print("4) Proof check — SUM(data rows) vs the sheet's own Total row:")
    import json
    for row in sql.query(
        "SELECT sheet, table_name, columns FROM orca_catalog "
        "WHERE company_id = ? AND file_id = ?", (COMPANY, FILE_ID),
    ):
        table, col_map = row["table_name"], json.loads(row["columns"])
        for orig, safe in col_map.items():
            # only check columns SQLite stored as REAL (our number columns)
            col_type = next((c[2] for c in sql.query(f'PRAGMA table_info("{table}")')
                             if c[1] == safe), "")
            if col_type != "REAL":
                continue
            data_sum = sql.query(
                f'SELECT SUM("{safe}") s FROM "{table}" WHERE _orca_is_total = 0'
            )[0]["s"]
            total_row = sql.query(
                f'SELECT SUM("{safe}") s FROM "{table}" WHERE _orca_is_total = 1'
            )[0]["s"]
            if total_row is None:
                continue  # this column has no printed total to compare against
            verdict = "MATCH" if data_sum is not None and abs(data_sum - total_row) < 0.01 else "MISMATCH"
            print(f"   {row['sheet']}.{orig}: sum={data_sum} vs total-row={total_row} -> {verdict}")

    sql.close()
    print("Done.")


if __name__ == "__main__":
    main()
