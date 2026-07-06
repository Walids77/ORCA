"""End-to-end test of the PDF table->SQL tidy stage (Session 8, Option B).

Extract a PDF -> tidy its tables (stitch / type / flag / classify) -> store the
number-tables in SQLite -> then the ACCURACY PROOF (same as the Excel one):
for every numeric column, SUM of the data rows must equal the value printed in
the document's own Total row. If the PDF has no total row, we just show the
sums for eyeball checking.

    ./.venv/Scripts/python.exe scripts/test_pdf_tables.py "data/Draft+order+June+2026.pdf"
"""
import sys
import logging

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from orca.ingest.pdf_processor import extract_pdf
from orca.ingest.pdf_tables import tidy_pdf_tables
from orca.stores.sql_store import SqlStore

PDF = sys.argv[1] if len(sys.argv) > 1 else "data/Draft+order+June+2026.pdf"
DB = "data/stores/orca.db"
COMPANY, FILE_ID = "demo", "pdf_tables_test"

print(f"1) Extracting: {PDF}")
extract = extract_pdf(PDF)
print(f"   {extract.page_count} pages, {len(extract.tables)} raw table grid(s)\n")

print("2) Tidying (stitch / type / flag / classify):")
sheets, report = tidy_pdf_tables(extract)
for r in report:
    stitched = f", stitched from {r['stitched_from']} page-grids" if r["stitched_from"] > 1 else ""
    print(f"   {r['sheet']}: pages {r['pages']}, {r['n_rows']}x{r['n_cols']}"
          f"{stitched}, {r['total_rows_flagged']} total-row(s) flagged")
    print(f"      -> {r['verdict']}  (numeric cols: {r['numeric_columns'] or 'none'})")

print(f"\n3) Storing {len(sheets)} number-table(s) -> {DB}")
store = SqlStore(DB)
store.store_pdf_tables(COMPANY, FILE_ID, sheets)

print("\n4) ACCURACY PROOF - SUM(data rows) vs the document's own Total row:")
any_total = False
for sheet in sheets:
    agg = set(sheet.aggregate_rows)
    for col, meta in sheet.column_meta.items():
        if not meta["is_numeric"]:
            continue
        data_sum = sum(r[col] for i, r in enumerate(sheet.rows)
                       if i not in agg and isinstance(r.get(col), (int, float)))
        totals = [r[col] for i, r in enumerate(sheet.rows)
                  if i in agg and isinstance(r.get(col), (int, float))]
        if totals:
            any_total = True
            # a summary ladder holds several derived values (discount, balance…);
            # the raw sum only needs to match ONE of them (the true total line).
            match = next((p for p in totals if abs(data_sum - p) < 0.01), None)
            if match is not None:
                print(f"   [PASS] {sheet.sheet_name}.{col}: sum(data)={data_sum:g} "
                      f"= a printed summary value ({match:g})")
            else:
                print(f"   [FAIL] {sheet.sheet_name}.{col}: sum(data)={data_sum:g} "
                      f"matches none of the printed summary values {totals}")
        else:
            print(f"   [no total row] {sheet.sheet_name}.{col}: sum(data)={data_sum:g}")
if not any_total:
    print("   (no printed totals found to check against - eyeball the sums above)")

print("\n4b) ROW-MATH PROOF - per data row: Cost x Quantity = Total Cost?")
for sheet in sheets:
    cols = {c.lower(): c for c in sheet.columns}
    cost = next((cols[k] for k in cols if "cost" in k and "total" not in k), None)
    qty = next((cols[k] for k in cols if "quantity" in k or "qty" in k), None)
    total = next((cols[k] for k in cols if "total" in k), None)
    if not (cost and qty and total):
        continue
    agg = set(sheet.aggregate_rows)
    n_ok = n_bad = n_skip = 0
    for i, r in enumerate(sheet.rows):
        if i in agg:
            continue
        c, q, t = r.get(cost), r.get(qty), r.get(total)
        if not all(isinstance(v, (int, float)) for v in (c, q, t)):
            n_skip += 1                     # incomplete row (messy source cell)
            continue
        if abs(c * q - t) < 0.05:
            n_ok += 1
        else:
            n_bad += 1
            print(f"   [MISMATCH] {sheet.sheet_name} row {i+1}: "
                  f"{c} x {q} = {c*q:g}, but the PDF says {t}")
    print(f"   {sheet.sheet_name}: {n_ok} rows check out, "
          f"{n_bad} mismatch(es), {n_skip} skipped (incomplete)")

print("\n5) Sample rows via SQL (read-only, parameterised):")
for row in store.catalog():
    if row["file_id"] != FILE_ID:
        continue
    t = row["table_name"]
    print(f"   -- {row['sheet']} ({row['row_count']} rows) --")
    for r in store.query(f'SELECT * FROM "{t}" LIMIT 3'):
        shown = {k: r[k] for k in r.keys() if not k.startswith("_orca_")}
        print(f"      {shown}")
store.close()
