"""The NUMBERS leg — answer exact-number questions from the SQL store.

Two moves, deliberately separated (the "caged" design locked in Session 11):

  MOVE 1 — the LLM PLANS: it sees the data catalog (which sheets + columns
  exist) and the question, and fills a small structured FORM: which sheet,
  which operation (SUM/AVG/...), which column, which filters. It never writes
  SQL and never sees the database.

  MOVE 2 — OUR CODE EXECUTES: it validates every form field against the
  catalog (unknown sheet/column/operation = rejected), builds the SQL itself
  from the catalog's own sanitised names, passes all values as parameters,
  and always excludes the flagged Total rows from aggregation.

So the LLM chooses, tested code executes — no LLM-written SQL ever runs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from orca.brain.llm import ask
from orca.stores.sql_store import SqlStore

logger = logging.getLogger(__name__)

# Session 16 — catalog MEANINGS: one plain-English line per sheet, written by
# the tenant (git-ignored — real business wording stays private). The catalog
# alone gives the planner NAMES; this gives it MEANINGS, so ambiguous words
# ("what was bought") map to the right sheet (client sales vs company spending
# — the Session-15 December wrong-sheet failure).
MEANINGS_PATH = Path("data/sheet_meanings.json")


def load_meanings(path: Path = MEANINGS_PATH) -> dict:
    """{file_id: {sheet: one-line meaning}} — missing file = no meanings."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No usable sheet meanings at %s (%s)", path, exc)
        return {}

# The only operations the executor will ever run (the cage's whitelist).
# LIST = return the matching rows themselves (for "show me..." questions),
# still read-only, still capped, still validated against the catalog.
_OPERATIONS = {"SUM", "AVG", "MIN", "MAX", "COUNT", "LIST"}
# The only filter comparisons allowed, mapped to their SQL shape.
_FILTER_OPS = {
    "=": "= ?", "!=": "!= ?", ">": "> ?", ">=": ">= ?",
    "<": "< ?", "<=": "<= ?",
    "contains": "LIKE ?",          # value gets wrapped in %...% below
}
_MAX_GROUP_ROWS = 10               # top-N cap when grouping (keeps answers short)
# Raised 20 -> 40 in Session 15: the depth branch made LIST the month-detail
# engine (a busy month holds ~37 sales rows) — the Session-14 watch item.
_MAX_LIST_ROWS = 40                # row cap for LIST answers (never dump a sheet)


# ── the catalog the planner sees ─────────────────────────────────────────────
def load_catalog(sql: SqlStore, company_id: str,
                 allowed_files: set[str] | None = None) -> list[dict]:
    """One entry per stored sheet: names, columns + types, and a sample row.

    allowed_files = the RBAC fence (Session 15): OUR code decides which files
    this user's catalog may contain, BEFORE any LLM sees it. None = no
    restriction (single-user today); the multi-user layer later passes the
    per-role set here — a data change, not a redesign.
    """
    meanings = load_meanings()
    entries = []
    for row in sql.query(
        "SELECT file_id, sheet, table_name, columns, row_count FROM orca_catalog "
        "WHERE company_id = ?", (company_id,),
    ):
        if allowed_files is not None and row["file_id"] not in allowed_files:
            continue
        col_map = json.loads(row["columns"])           # original name -> safe SQL name
        # Column types come from the table itself (REAL = number, TEXT = text/date).
        types = {c["name"]: c["type"] for c in sql.query(f'PRAGMA table_info("{row["table_name"]}")')}
        sample = sql.query(
            f'SELECT * FROM "{row["table_name"]}" WHERE _orca_is_total = 0 LIMIT 1'
        )
        sample_row = {}
        if sample:
            d = dict(sample[0])
            sample_row = {orig: d.get(safe) for orig, safe in col_map.items()}
        entries.append({
            "file_id": row["file_id"],
            "sheet": row["sheet"],
            "table_name": row["table_name"],
            "row_count": row["row_count"],
            "col_map": col_map,
            "col_types": {orig: ("number" if types.get(safe) == "REAL" else "text")
                          for orig, safe in col_map.items()},
            "sample_row": sample_row,
            # the tenant's one-line meaning for this sheet ("" = none written)
            "meaning": (meanings.get(row["file_id"]) or {}).get(row["sheet"], ""),
        })
    return entries


def catalog_text(catalog: list[dict]) -> str:
    """The plain-text 'menu' of the tenant's data, shown to the planner LLM."""
    lines = []
    for e in catalog:
        cols = ", ".join(f"{name} ({t})" for name, t in e["col_types"].items())
        lines.append(f"- sheet \"{e['sheet']}\" (file {e['file_id']}, {e['row_count']} rows)")
        if e.get("meaning"):
            lines.append(f"    meaning: {e['meaning']}")
        lines.append(f"    columns: {cols}")
        if e["sample_row"]:
            sample = ", ".join(f"{k}={str(v)[:30]}" for k, v in e["sample_row"].items()
                               if v not in (None, ""))
            lines.append(f"    example row: {sample}")
    return "\n".join(lines)


# ── MOVE 1: the LLM fills the form ───────────────────────────────────────────
def plan_query(question: str, menu: str) -> dict:
    """Ask the LLM which computation would answer the question. Returns the form
    as a dict; {"needed": false} when the question isn't a numbers question."""
    prompt = (
        "You are the query PLANNER for a business data assistant. Below is the "
        "catalog of the company's spreadsheet data, then a user question.\n\n"
        "If the question needs an EXACT NUMBER computed from this data, or a "
        "LIST of matching rows, reply with ONLY a JSON object (no prose, no "
        "code fences) in this shape:\n"
        '{"needed": true, "sheet": "<sheet name from the catalog>", '
        '"operation": "SUM"|"AVG"|"MIN"|"MAX"|"COUNT"|"LIST", '
        '"column": "<column to aggregate, or null for COUNT of rows / LIST>", '
        '"filters": [{"column": "<column>", "op": "="|"!="|">"|">="|"<"|"<="|"contains", '
        '"value": <number or string>}], '
        '"group_by": "<column to group by, or null>", '
        '"columns": ["<for LIST only: which columns to show>"]}\n\n'
        "Rules:\n"
        "- Use ONLY sheet and column names that appear in the catalog, exactly as written.\n"
        "- Dates are stored as ISO text like 2026-05-28T00:00:00 — to filter a month, "
        "use op \"contains\" with e.g. \"2026-05\".\n"
        "- For \"best/top X by ...\" questions, use group_by on the label column and "
        "SUM (or COUNT) on the measure.\n"
        "- For \"show me / list the rows that ...\" questions, use operation LIST "
        "with filters, and name the useful columns in \"columns\".\n"
        "- Questions asking WHAT was bought/sold/mentioned (not how much) are "
        "LIST questions — use LIST and include the remark/description column "
        "in \"columns\": the remarks describe the items.\n"
        "- If the catalog has NO column holding what the question asks about (e.g. "
        "it asks per client but no sheet has a client-name column), reply "
        '{"needed": false} rather than guessing a wrong column.\n'
        "- If the question does NOT need a computed number or row list from this "
        'data, reply with ONLY: {"needed": false}\n\n'
        f"CATALOG:\n{menu}\n\nQUESTION: {question}"
    )
    raw = ask(prompt, purpose="numbers-form").strip()
    # Tolerate a model that wraps the JSON in ``` fences despite the instruction.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
    try:
        plan = json.loads(raw)
        if not isinstance(plan, dict):
            raise ValueError("plan is not an object")
        return plan
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Planner returned unusable JSON (%s): %r", exc, raw[:200])
        return {"needed": False, "error": f"planner output not valid JSON: {exc}"}


# ── MOVE 2: our code validates the form and runs the query ──────────────────
def run_plan(sql: SqlStore, catalog: list[dict], plan: dict) -> dict:
    """Execute a validated plan. Every identifier must exist in the catalog;
    every value is parameterised; Total rows are always excluded."""
    if not plan.get("needed"):
        return {"needed": False}

    entry = next((e for e in catalog if e["sheet"] == plan.get("sheet")), None)
    if entry is None:
        return {"needed": True, "error": f"unknown sheet {plan.get('sheet')!r}"}
    col_map = entry["col_map"]

    op = str(plan.get("operation", "")).upper()
    if op not in _OPERATIONS:
        return {"needed": True, "error": f"operation {op!r} not allowed"}

    column = plan.get("column")
    agg_sql = measure = ""
    if op == "LIST":
        measure = "matching rows"
    elif op == "COUNT" and column in (None, "", "*"):
        agg_sql = "COUNT(*)"
        measure = "row count"
    else:
        if column not in col_map:
            return {"needed": True, "error": f"unknown column {column!r}"}
        agg_sql = f'{op}("{col_map[column]}")'
        measure = f"{op} of {column}"

    # WHERE: tenant fence + never aggregate the sheet's own Total rows.
    where = ["_orca_file = ?", "_orca_is_total = 0"]
    params: list[Any] = [entry["file_id"]]
    applied_filters = []
    for f in plan.get("filters") or []:
        fcol, fop, fval = f.get("column"), f.get("op"), f.get("value")
        if fcol not in col_map:
            return {"needed": True, "error": f"unknown filter column {fcol!r}"}
        if fop not in _FILTER_OPS:
            return {"needed": True, "error": f"filter op {fop!r} not allowed"}
        where.append(f'"{col_map[fcol]}" {_FILTER_OPS[fop]}')
        params.append(f"%{fval}%" if fop == "contains" else fval)
        applied_filters.append(f"{fcol} {fop} {fval}")

    table = entry["table_name"]
    group_by = plan.get("group_by")
    if op == "LIST":
        # Which columns to show: the planner's picks (validated), else all.
        wanted = [c for c in (plan.get("columns") or []) if c in col_map] \
                 or list(col_map.keys())
        select = ", ".join(f'"{col_map[c]}" AS "{c}"' for c in wanted)
        query = (f'SELECT {select} FROM "{table}" '
                 f'WHERE {" AND ".join(where)} LIMIT {_MAX_LIST_ROWS}')
        rows = [dict(r) for r in sql.query(query, tuple(params))]
    elif group_by:
        if group_by not in col_map:
            return {"needed": True, "error": f"unknown group_by column {group_by!r}"}
        gcol = col_map[group_by]
        query = (f'SELECT "{gcol}" AS grp, {agg_sql} AS value FROM "{table}" '
                 f'WHERE {" AND ".join(where)} GROUP BY "{gcol}" '
                 f'ORDER BY value DESC LIMIT {_MAX_GROUP_ROWS}')
        rows = [{"group": r["grp"], "value": r["value"]} for r in sql.query(query, tuple(params))]
    else:
        query = f'SELECT {agg_sql} AS value FROM "{table}" WHERE {" AND ".join(where)}'
        rows = [{"value": sql.query(query, tuple(params))[0]["value"]}]

    return {
        "needed": True,
        "sheet": entry["sheet"],
        "computed": measure,
        "filters": applied_filters,
        "group_by": group_by,
        "rows": rows,
        # for transparency / the trace — what actually ran (no user text inside)
        "sql": query,
    }


def result_text(result: dict) -> str:
    """Render the computed result as a small evidence block for the answer-writer."""
    if not result.get("needed"):
        return ""
    if result.get("error"):
        return f"(numbers leg could not compute: {result['error']})"
    parts = [f"Computed from sheet \"{result['sheet']}\" (Total rows excluded): {result['computed']}"]
    if result["filters"]:
        parts.append(f"filtered by {'; '.join(result['filters'])}")
    if result.get("group_by"):
        parts.append(f"grouped by {result['group_by']}, highest first")
    lines = [", ".join(parts) + ":"]

    # LIST answers: the matching rows themselves, one line each.
    if result.get("computed") == "matching rows":
        if not result["rows"]:
            lines.append("  NO DATA — no rows match these filters. "
                         "The uploaded data contains nothing for this question.")
        for r in result["rows"]:
            cells = ", ".join(f"{k}: {v}" for k, v in r.items() if v is not None)
            lines.append(f"  - {cells}")
        return "\n".join(lines)

    # A SUM/AVG over zero matching rows comes back as None — that means the data
    # simply has nothing for these filters. Say so EXPLICITLY, otherwise the
    # answer-writer may echo a meaningless "None" instead of declining.
    values = [r["value"] for r in result["rows"]]
    if not values or all(v is None for v in values):
        lines.append("  NO DATA — the query matched no rows for these filters. "
                     "The uploaded data contains nothing for this question.")
        return "\n".join(lines)
    for r in result["rows"]:
        if "group" in r:
            lines.append(f"  {r['group']}: {r['value']}")
        else:
            lines.append(f"  value = {r['value']}")
    return "\n".join(lines)
