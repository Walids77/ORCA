"""ORCA PDF table tidy — turn Docling's raw text grids into typed SQL tables.

Docling (stage 1) hands each PDF table over as a faithful grid of TEXT — a cell
says "$1,234.56", not the number 1234.56. You cannot SUM text. This stage makes
number-tables SQL-ready, reusing the Excel processor's proven logic:

  1. STITCH  — a long table becomes one grid PER PAGE in the PDF; consecutive
               grids with the same cleaned headers are glued back into ONE table
               (the "headers across pages" problem).
  2. TYPE    — every cell is parsed: "$1,234.56" -> 1234.56, "(500)" -> -500,
               "12%" -> 12.0, "1,000" -> 1000, date strings -> real dates,
               blanks/"NA" -> None. Text stays text.
  3. FLAG    — Total/summary rows are detected (the Excel detector, reused) so a
               grand-total row never double-counts in a SUM.
  4. CLASSIFY— number-table (has clearly numeric columns) -> ships to the SQL
               store; word-table (a comparison/text grid) -> skipped here, it is
               already embedded as text by the chunker for meaning search.

Output = the Excel processor's own `SheetTable` shape, so the existing SqlStore
stores PDF tables UNCHANGED — same security sanitising, same citation metadata,
same catalog. (Session 8, Option B.)
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from typing import Any

from orca.ingest.excel_processor import (
    SheetTable,
    _cell_kind,
    _clean_column_names,
    _detect_aggregate_rows,
    _is_blank,
    _tag_columns,
)
from orca.ingest.pdf_processor import PdfExtract, PdfTable

logger = logging.getLogger(__name__)

# =============================================================================
# STAGE 2 (TYPE) - parse one text cell into a real typed value
# =============================================================================
# Currency markers we strip before trying to read a number. Symbols or codes,
# before or after the digits ("$1,234", "1 234 AED", "USD 50").
_CCY = r"(?:[$€£¥]|aed|usd|eur|gbp|lbp|sar|chf)"
_CCY_PREFIX = re.compile(rf"^{_CCY}\s*", re.IGNORECASE)
_CCY_SUFFIX = re.compile(rf"\s*{_CCY}$", re.IGNORECASE)

# A number: optional sign, digits with optional thousands-commas, optional
# decimals. Full-match only — "3 boxes of 12" must NOT become a number.
_NUMBER_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^[+-]?\d+(?:\.\d+)?$")

# Date shapes we try, most common first. Full-match via strptime.
_DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y",
)


def _parse_number(text: str) -> int | float | None:
    """Read a number out of a text cell, or None if it isn't one.

    Handles: "$1,234.56" / "1,000" / "(500)" accounting-negative / "12%" /
    "AED 750". Percent keeps its face value: "12%" -> 12.0 (not 0.12) — the
    column NAME says it's a percent, the value stays what the page shows.
    """
    t = text.strip()
    negative = t.startswith("(") and t.endswith(")")
    if negative:
        t = t[1:-1].strip()
    is_percent = t.endswith("%")
    if is_percent:
        t = t[:-1].strip()
    t = _CCY_SUFFIX.sub("", _CCY_PREFIX.sub("", t)).strip()
    if not _NUMBER_RE.match(t):
        return None
    value = float(t.replace(",", ""))
    if negative:
        value = -value
    if is_percent:
        return value                      # keep percents as float (12.0)
    return int(value) if value.is_integer() else value


def _parse_date(text: str) -> _dt.datetime | None:
    """Read a date out of a text cell, or None if it isn't one."""
    t = text.strip()
    if len(t) < 6 or len(t) > 20:         # too short/long to be a date
        return None
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None


def _type_cell(text: Any) -> Any:
    """One PDF cell (text) -> typed value: number / date / clean text / None."""
    if _is_blank(text):
        return None
    s = str(text)
    number = _parse_number(s)
    if number is not None:
        return number
    date = _parse_date(s)
    if date is not None:
        return date
    return s.strip()


# =============================================================================
# STAGE 1 (STITCH) - glue a table that continues across pages back together
# =============================================================================
# A table that runs over several pages comes back as one grid PER PAGE, and the
# continuation pages usually have BROKEN headers, one of three ways:
#   a) the header row is re-printed        -> headers match the first page
#   b) there is no header row              -> Docling makes generic ones (0,1,2…)
#   c) the FIRST DATA ROW is mistaken for the header ("$2.59" as a column name!)
# Case (c) silently LOSES a data row unless we rescue it back into the rows.
def _norm_cols(columns: list[str]) -> tuple[str, ...]:
    """Column names normalised for comparison (case/space-insensitive)."""
    return tuple(re.sub(r"\s+", " ", str(c).strip().lower()) for c in columns)


_GENERIC_COL = re.compile(r"^(\d+|unnamed[:_ ]*\d*|column[_ ]?\d+|)$", re.IGNORECASE)


def _headers_generic(columns: list[str]) -> bool:
    """True if EVERY column name is a placeholder (0,1,2 / Unnamed / blank)."""
    return all(_GENERIC_COL.match(str(c).strip()) for c in columns)


def _headers_look_like_data(columns: list[str]) -> bool:
    """True if any 'column name' parses as a number — real headers never do."""
    return any(_parse_number(str(c)) is not None for c in columns)


def _stitch(tables: list[PdfTable]) -> list[dict]:
    """Group consecutive page-grids that are really ONE table.

    A grid continues the previous group when it sits on the same/next page, has
    the same column COUNT, and its headers are (a) identical, (b) generic
    placeholders, or (c) really a data row. In case (c) the header row is
    rescued as data. Returns groups: {columns, pages, raw_rows, n_grids}, where
    raw_rows are positional value-lists (cell order, not names).
    """
    groups: list[dict] = []
    for table in tables:
        cols = [str(c) for c in table.columns]
        value_rows = [list(r.values()) for r in table.rows]
        if groups:
            g = groups[-1]
            adjacent = table.page in (g["pages"][-1], g["pages"][-1] + 1)
            same_count = len(cols) == len(g["columns"])
            if adjacent and same_count:
                if _norm_cols(cols) == _norm_cols(g["columns"]):
                    rescued = []                       # (a) header re-printed
                elif _headers_generic(cols):
                    rescued = []                       # (b) no header at all
                elif _headers_look_like_data(cols):
                    rescued = [cols]                   # (c) header IS a data row
                else:
                    rescued = None                     # different table
                if rescued is not None:
                    g["raw_rows"] += rescued + value_rows
                    g["pages"].append(table.page)
                    g["n_grids"] += 1
                    continue
        groups.append({
            "columns": cols,
            "pages": [table.page],
            "raw_rows": value_rows,
            "n_grids": 1,
        })
    return groups


# =============================================================================
# STAGE 3b (FLAG) - structural summary-row detection, PDF-specific
# =============================================================================
# The Excel detector (reused below) flags rows by KEYWORD ("Total", "Subtotal").
# PDF order/invoice tables often end with a summary LADDER whose labels vary
# wildly ("Initial", "15% discount", "Final to pay"...). Those rows share a
# SHAPE, not a word: almost all cells empty, one short text label, one number.
def _detect_label_value_rows(columns: list[str], rows: list[dict[str, Any]]) -> list[int]:
    """Indices of rows that are a label+value summary line, not a data row."""
    if len(columns) < 4:                   # too narrow to tell shape apart
        return []
    flagged = []
    for i, row in enumerate(rows):
        filled = [v for v in row.values() if v is not None]
        if len(filled) > 2:                # real data rows fill 3+ cells
            continue
        labels = [v for v in filled if isinstance(v, str)]
        numbers = [v for v in filled if isinstance(v, (int, float))]
        if len(numbers) == 1 and len(labels) <= 1 and \
                all(len(s) <= 25 for s in labels):
            flagged.append(i)
    return flagged


# =============================================================================
# STAGE 4 (CLASSIFY) - number-table (to SQL) vs word-table (vector-only)
# =============================================================================
def _numeric_columns(columns: list[str], rows: list[dict[str, Any]]) -> list[str]:
    """Columns whose non-empty values are mostly (>=60%) real numbers."""
    numeric = []
    for col in columns:
        values = [r.get(col) for r in rows if r.get(col) is not None]
        if not values:
            continue
        n_num = sum(1 for v in values if _cell_kind(v) == "number")
        if n_num / len(values) >= 0.6:
            numeric.append(col)
    return numeric


# =============================================================================
# THE MAIN ENTRY POINT
# =============================================================================
def tidy_pdf_tables(extract: PdfExtract) -> tuple[list[SheetTable], list[dict]]:
    """Stitch + type + flag + classify every table Docling found in a PDF.

    Returns (number_sheets, report):
      - number_sheets: SheetTable objects ready for SqlStore (number-tables only)
      - report: one dict per stitched table (pages, size, verdict, numeric cols)
                so a caller/test can SEE what was classified and why.
    """
    number_sheets: list[SheetTable] = []
    report: list[dict] = []

    for n, group in enumerate(_stitch(extract.tables), start=1):
        pages = sorted(set(group["pages"]))
        columns = _clean_column_names(group["columns"])

        # type the group's rows, keyed positionally to the cleaned column names.
        rows: list[dict[str, Any]] = []
        for raw_vals in group["raw_rows"]:
            if _norm_cols([str(v) for v in raw_vals]) == _norm_cols(columns):
                continue                           # repeated header row
            typed = {col: _type_cell(v) for col, v in zip(columns, raw_vals)}
            if all(v is None for v in typed.values()):
                continue                           # fully blank line
            rows.append(typed)

        # flag summary rows two ways: by KEYWORD (Excel detector, "Total"...)
        # and by SHAPE (label+value ladder: "Initial", "Final to pay"...).
        aggregate_rows = sorted(set(_detect_aggregate_rows(rows))
                                | set(_detect_label_value_rows(columns, rows)))
        numeric_cols = _numeric_columns(columns, rows)
        is_number_table = bool(numeric_cols) and len(rows) > 0

        sheet_name = f"pdf_table_{n}_p{pages[0]}"
        report.append({
            "sheet": sheet_name,
            "pages": pages,
            "n_rows": len(rows), "n_cols": len(columns),
            "numeric_columns": numeric_cols,
            "total_rows_flagged": len(aggregate_rows),
            "stitched_from": group["n_grids"],
            "verdict": "number-table -> SQL" if is_number_table
                       else "word-table -> vector-only",
        })
        if not is_number_table:
            continue

        number_sheets.append(SheetTable(
            sheet_name=sheet_name,
            header_row=0,                          # no Excel row concept in a PDF
            columns=columns,
            rows=rows,
            # 1-based row number INSIDE this table (citations: "table row 3");
            # the page lives in the sheet name + note.
            source_rows=list(range(1, len(rows) + 1)),
            note=f"PDF table, page(s) {','.join(str(p) for p in pages)}",
            aggregate_rows=aggregate_rows,
            column_meta=_tag_columns(columns, rows, aggregate_rows),
        ))

    logger.info("PDF tables: %d found, %d stitched group(s), %d number-table(s) to SQL",
                len(extract.tables), len(report), len(number_sheets))
    return number_sheets, report
