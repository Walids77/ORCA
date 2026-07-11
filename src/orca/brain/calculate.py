"""The caged CALCULATE worker — Session 16: the plan's third lane.

The arithmetic gap closed the caged way (Walid's Session-11 design): the
PLANNER picks a function from this whitelist and names which step answers
feed it — OUR code extracts those exact numbers and does the math. The LLM
never computes; there is no LLM call anywhere in this file.

Every function here is tested, takes plain numbers, and returns one number.
First eval case (source-verified): average basket = SUM(sales) ÷ COUNT(invoices)
= 26,303.85 ÷ 1,077 = 24.42 — matches the sheet's own Total row.
"""

from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"\{step (\d+)\}")


# ── the whitelist: name -> (how many inputs, the tested function, meaning) ────
def _divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def _difference(a: float, b: float) -> float:
    return a - b


def _percent_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("percent change from zero")
    return (new - old) / old * 100.0


def _projection(base: float, percent: float) -> float:
    return base * (1.0 + percent / 100.0)


FUNCTIONS: dict[str, tuple[int, object, str]] = {
    "divide": (2, _divide, "a ÷ b (ratios, averages like total ÷ count)"),
    "ratio": (2, _divide, "same as divide"),
    "difference": (2, _difference, "a − b"),
    "percent_change": (2, _percent_change,
                       "growth from the FIRST number to the SECOND, in %"),
    "projection": (2, _projection,
                   "first number grown by the given percent (e.g. base, 10 = +10%)"),
}


# ── pulling the exact number OUT of a feeding step's result ──────────────────
def step_number(result: dict) -> float:
    """The single numeric value a finished step produced. Raises ValueError
    with a plain reason when the step's answer isn't one number — the
    calculate step then fails alone with that reason (never a wrong figure)."""
    lane = result.get("lane")
    if lane == "text":
        raise ValueError("a text step returns passages, not a number")
    r = result.get("result") or {}
    if not r.get("needed") or r.get("error"):
        raise ValueError(f"feeding step has no result ({r.get('error') or 'no data'})")
    if lane == "calculate":
        return float(r["rows"][0]["value"])
    if r.get("computed") == "matching rows":
        raise ValueError("a LIST step returns rows, not a single number")
    rows = r.get("rows") or []
    if not rows or rows[0].get("value") is None:
        raise ValueError("feeding step returned no data")
    # Grouped/ranked results: the top row's value (highest first by design).
    return float(rows[0]["value"])


def _resolve_input(inp: object, step_results: dict) -> float:
    """An input is either a {step N} placeholder (that step's number) or a
    plain number written in the plan (e.g. the +10% assumption)."""
    if isinstance(inp, (int, float)) and not isinstance(inp, bool):
        return float(inp)
    m = _PLACEHOLDER.fullmatch(str(inp).strip())
    if m:
        n = int(m.group(1))
        if n not in step_results:
            raise ValueError(f"step {n} has not answered yet")
        return step_number(step_results[n])
    # A bare number arriving as text ("10") still counts as a literal.
    try:
        return float(str(inp).strip())
    except ValueError:
        raise ValueError(f"input {inp!r} is neither a number nor a {{step N}} placeholder")


# ── MOVE 2 only — there is no MOVE 1: the plan already holds the form ────────
def run_calculation(step: dict, step_results: dict) -> dict:
    """Execute one calculate step. Same result shape as the numbers leg
    ({"needed", "computed", "rows", "error"}) so every downstream reader —
    step_answer_text, the combine — handles it with the same code paths."""
    name = str(step.get("function") or "").strip().lower()
    entry = FUNCTIONS.get(name)
    if entry is None:
        return {"needed": True, "error": f"function {name!r} not in the whitelist"}
    arity, fn, _ = entry
    inputs = step.get("inputs") or []
    if len(inputs) != arity:
        return {"needed": True,
                "error": f"{name} needs {arity} inputs, got {len(inputs)}"}
    try:
        values = [_resolve_input(i, step_results) for i in inputs]
        value = fn(*values)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        return {"needed": True, "error": f"calculation failed: {exc}"}
    return {
        "needed": True,
        "computed": f"{name}({', '.join(str(v) for v in values)})",
        "rows": [{"value": value}],
    }


def calc_result_text(result: dict) -> str:
    """Render a calculate result as a small evidence block for the answer-writer
    (the numbers leg's result_text needs sheet/filter fields this lane
    doesn't have)."""
    if not result.get("needed"):
        return ""
    if result.get("error"):
        return f"(calculate step could not compute: {result['error']})"
    value = result["rows"][0]["value"]
    return (f"Calculated by ORCA's own tested math code (never the AI): "
            f"{result['computed']}:\n  value = {value}")
