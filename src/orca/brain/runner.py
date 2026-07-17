"""The PLAN-RUNNER — Session 15: execute the planner's checklist in WAVES.

ONE station with a capped loop-back edge. Each visit = one WAVE:
run ALL steps whose dependencies are already answered — in parallel, through
the SAME proven legs (hybrid text search · caged numbers form → SQL; no new
engines) — then write the results into the notebook. Between waves the
{step N} placeholders (and "waits-for" context) are filled from the notebook.

Time stretches with DEPTH (number of waves), cost with TOTAL steps — the
fixed map, dynamic plan design Walid locked in Session 14.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from orca.brain.calculate import run_calculation
from orca.brain.numbers import plan_query, run_plan, result_text
from orca.brain.planner import MAX_STEPS, _PLACEHOLDER
from orca.brain.state import Notebook
from orca.stores.hybrid import HybridSearcher
from orca.stores.sql_store import SqlStore

# The loop cap: a valid plan of N steps never needs more than N waves, and the
# cage already limits N — so the runner can never spin forever.
MAX_WAVES = MAX_STEPS


# ── rendering an answered step so a LATER step can use it ────────────────────
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-\d{2}(?:[T ][\d:.]*)?$")
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def _pretty(value: object) -> str:
    """Wording for a value that will ride inside a QUESTION. An ISO date like
    2026-02-27T00:00:00 becomes 'February 2026 (2026-02)' — the human words
    carry the meaning, the ISO month carries the exact filter token. Both
    halves earned their place in the Session-15 eval: a raw timestamp made
    text search retrieve garbage, and 'February' alone left the numbers form
    unable to build its date filter."""
    s = str(value)
    m = _ISO_DATE.match(s)
    if m:
        return (f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)} "
                f"({m.group(1)}-{m.group(2)})")
    return s


def step_answer_text(result: dict) -> str:
    """A compact, plain-text rendering of one step's answer — small enough to
    sit inside the next step's question."""
    if result.get("lane") == "text":
        hits = result.get("hits") or []
        if not hits:
            return "(no passages found)"
        previews = [" ".join(h.get("text", "").split())[:150] for h in hits[:2]]
        return " / ".join(previews)
    r = result.get("result") or {}
    if not r.get("needed") or r.get("error"):
        return "(no data)"
    rows = r.get("rows") or []
    if not rows:
        return "(no data)"
    if "group" in rows[0]:                       # ranked groups: top row first
        # The LABEL alone (e.g. "February 2026 (2026-02)") — never the figure.
        # Session-15 eval: a "(value 1755.0)" suffix made the numbers form add
        # a bogus filter Net Sales = 1755.0 and return zero rows. The figure
        # reaches the final answer through the computing step's own block.
        return _pretty(rows[0]["group"])
    if r.get("computed") == "matching rows":     # LIST result feeding a later step
        # Session 25 guard (from the S24 duel): a MULTI-row list pasted into a
        # question poisons the next step's form/search — the step reads like
        # gibberish and answers "no info". One row can ride along; many rows =
        # say so honestly and let the next step decline instead of derail.
        if len(rows) == 1:
            return ", ".join(f"{k}: {_pretty(v)}" for k, v in rows[0].items()
                             if v is not None)
        return (f"(the earlier step returned a list of {len(rows)} rows, "
                "not a single value)")
    return str(rows[0].get("value"))


def _fill_question(step: dict, step_results: dict) -> str:
    """Put the earlier answers INTO the step's question: replace {step N}
    placeholders, and (because the planner sometimes writes 'identified in
    step 1' instead of a placeholder) always attach the waited-for answers as
    known context — no dependency gets lost either way."""
    question = step["question"]
    filled = _PLACEHOLDER.sub(
        lambda m: step_answer_text(step_results.get(int(m.group(1)), {})),
        question,
    )
    context = [
        f"step {n} answered: {step_answer_text(step_results[n])}"
        for n in step["waits_for"]
        if n in step_results and f"{{step {n}}}" not in question
    ]
    if context:
        filled += "\n(Known from earlier steps: " + "; ".join(context) + ")"
    return filled


# ── the runner station ───────────────────────────────────────────────────────
def make_plan_runner_node(text_searcher: HybridSearcher, sql: SqlStore,
                          catalog: list[dict], menu: str, k: int = 5):
    """catalog/menu arrive already RBAC-filtered (built once in graph.py)."""

    def run_one_step(step: dict, step_results: dict) -> dict:
        question = _fill_question(step, step_results)
        try:
            if step["lane"] == "text":
                return {"lane": "text", "question": question,
                        "hits": text_searcher.search(question, k=k)}
            if step["lane"] == "calculate":
                # Session 16: no LLM here — the plan already names the function
                # and inputs; our whitelisted code does the math.
                return {"lane": "calculate", "question": question,
                        "result": run_calculation(step, step_results)}
            form = plan_query(question, menu)        # MOVE 1: the LLM fills the form
            result = run_plan(sql, catalog, form)    # MOVE 2: our code runs the SQL
            return {"lane": "numbers", "question": question, "result": result}
        except Exception as exc:                     # noqa: BLE001
            # Session 16 safety net: a crashing step fails ALONE — combine
            # answers the parts that worked and names the part that didn't.
            return {"lane": step["lane"], "question": question,
                    "result": {"needed": True, "error": f"step failed: {exc}"}}

    def plan_runner_node(notebook: Notebook) -> dict:
        plan = notebook.get("plan") or []
        step_results = dict(notebook.get("step_results") or {})
        ready = [s for s in plan
                 if s["n"] not in step_results
                 and all(n in step_results for n in s["waits_for"])]
        if not ready:
            # Can't happen with a caged plan (deps always point earlier), but
            # never spin on an empty wave: mark leftovers unreachable and stop.
            for s in plan:
                step_results.setdefault(
                    s["n"], {"lane": s["lane"], "question": s["question"],
                             "result": {"needed": True, "error": "unreachable step"}})
        else:
            # THE WAVE: every ready step at once (the legs are thread-safe —
            # SqlStore went per-thread in Session 14).
            with ThreadPoolExecutor(max_workers=len(ready)) as pool:
                futures = {s["n"]: pool.submit(run_one_step, s, step_results)
                           for s in ready}
            for n, fut in futures.items():
                step_results[n] = fut.result()
        return {"step_results": step_results,
                "waves_run": (notebook.get("waves_run") or 0) + 1}

    return plan_runner_node


def more_waves(notebook: Notebook) -> str:
    """The loop-back junction: another wave while steps remain (capped)."""
    plan = notebook.get("plan") or []
    done = notebook.get("step_results") or {}
    if (any(s["n"] not in done for s in plan)
            and (notebook.get("waves_run") or 0) < MAX_WAVES):
        return "again"
    return "done"
