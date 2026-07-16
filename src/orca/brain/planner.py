"""The PLANNER — Session 15: the router grows into a plan-writer.

Instead of just picking a lane, the LLM writes a CHECKLIST into the notebook:
one row per step, each with a focused question, a lane (numbers/text), and a
waits-for list. A later step may carry the placeholder {step N} inside its
question — the plan-runner fills it with step N's answer between waves
(Walid's 2D depth axis; the same shape as the LLMCompiler pattern).

The cage (locked Session 14 close-out): OUR code validates the plan — real
lanes only, waits-for may only point to an EARLIER step, hard max steps — and
an unreadable plan falls back to the Session-14 both-lanes design, so a bad
plan can never do worse than no plan.
"""

from __future__ import annotations

import json
import logging
import re

from orca.brain.llm import ask
from orca.brain.calculate import FUNCTIONS
from orca.brain.state import Notebook

logger = logging.getLogger(__name__)

MAX_STEPS = 8                                  # the cage's hard ceiling
LANES = {"numbers", "text", "calculate"}       # the only engines that exist
_PLACEHOLDER = re.compile(r"\{step (\d+)\}")   # how a question carries a dependency


# ── the cage: validate what the LLM wrote ───────────────────────────────────
def validate_plan(raw: object) -> list[dict] | None:
    """Return the cleaned checklist, or None if the plan breaks any cage rule.

    Rules: 1..MAX_STEPS steps · every lane real · every waits-for (explicit or
    a {step N} placeholder) points to an EARLIER step only. Steps are renumbered
    1..n in the order the planner wrote them.
    """
    steps_in = raw.get("steps") if isinstance(raw, dict) else None
    if not isinstance(steps_in, list) or not (1 <= len(steps_in) <= MAX_STEPS):
        return None
    steps: list[dict] = []
    for i, s in enumerate(steps_in, 1):
        if not isinstance(s, dict):
            return None
        question = str(s.get("question") or "").strip()
        lane = str(s.get("lane") or "").strip().lower()
        if not question or lane not in LANES:
            return None
        waits: set[int] = set()
        for w in s.get("waits_for") or []:
            try:
                waits.add(int(w))
            except (TypeError, ValueError):
                return None
        # A {step N} placeholder in the question is a dependency too, even if
        # the planner forgot to list it.
        for m in _PLACEHOLDER.finditer(question):
            waits.add(int(m.group(1)))
        step = {"n": i, "question": question, "lane": lane}
        if lane == "calculate":
            # Session 16 cage: the function must be whitelisted, and every
            # {step N} input is a dependency exactly like a placeholder.
            function = str(s.get("function") or "").strip().lower()
            if function not in FUNCTIONS:
                return None
            inputs = s.get("inputs")
            if not isinstance(inputs, list) or not inputs:
                return None
            for inp in inputs:
                for m in _PLACEHOLDER.finditer(str(inp)):
                    waits.add(int(m.group(1)))
            step["function"] = function
            step["inputs"] = inputs
        if any(w < 1 or w >= i for w in waits):   # only EARLIER steps allowed
            return None
        step["waits_for"] = sorted(waits)
        steps.append(step)
    return steps


def fallback_plan(question: str) -> list[dict]:
    """Unreadable plan -> the Session-14 both-lanes shape: both engines get the
    raw question in one parallel wave. May waste a little work, never loses an
    answer to a parse error."""
    return [
        {"n": 1, "question": question, "lane": "numbers", "waits_for": []},
        {"n": 2, "question": question, "lane": "text", "waits_for": []},
    ]


# ── the planner station ──────────────────────────────────────────────────────
def make_planner_node(menu: str, doc_list: str):
    """menu + doc_list arrive already filtered by the RBAC fence (graph.py):
    the planner can only ever plan over data this user may see."""

    def planner_node(notebook: Notebook) -> dict:
        q = notebook["question"]
        prompt = (
            "You are the PLANNER for a business data assistant. Break the "
            "user's question into the SMALLEST checklist of steps that answers "
            "it. Each step runs on ONE engine:\n"
            '- "numbers": computes an exact figure or a list of matching rows '
            "from the spreadsheet data below (sum, average, count, min/max, "
            "ranking, list).\n"
            '- "text": finds passages by READING the text documents below '
            "(definitions, explanations, remarks, policies — no computation).\n"
            '- "calculate": ONE exact math operation on numbers from EARLIER '
            "steps. Functions (the only ones that exist):\n"
            "    divide(a, b) — a ÷ b (ratios, averages like total ÷ count)\n"
            "    difference(a, b) — a − b\n"
            "    percent_change(old, new) — growth from old to new, in %\n"
            "    projection(base, percent) — base grown by percent (10 = +10%)\n\n"
            f"SPREADSHEET CATALOG:\n{menu}\n\n"
            f"TEXT DOCUMENTS SEARCHABLE:\n{doc_list}\n"
            "(The spreadsheets' free-text remark columns are searchable as "
            "text too.)\n\n"
            "Rules:\n"
            "- Most questions need ONE step. Use more ONLY when the question "
            "truly has separate parts.\n"
            "- Independent parts = separate steps with empty \"waits_for\" "
            "(they will run at the same time).\n"
            "- Any step filtered by a SPECIFIC month/period (e.g. \"what was "
            "sold/bought then\", \"the remarks from that month\") MUST use the "
            "numbers lane — it lists the matching rows with their remarks, "
            "filtered exactly by date. The text lane has NO date filter and "
            "will miss. Use text only for meaning/topic lookups.\n"
            "- If a step can only be asked AFTER an earlier step's answer is "
            "known, write the placeholder {step N} where that answer belongs "
            "in its question, and put N in its \"waits_for\". Example: step 1 "
            'finds the top client; step 2 = "What do the remarks say about '
            '{step 1}?" with "waits_for": [1].\n'
            "- Each step's question must be plain and focused — one "
            "figure/lookup per step.\n"
            "- Each step's question must be SELF-CONTAINED: if the user names "
            "a company/brand/file (e.g. \"Acme\", \"the north branch\"), REPEAT "
            "that name inside every step's question. The step runs alone — a "
            "step that just says \"the sales\" cannot know whose sales, and "
            "several files hold sheets with the same names.\n"
            "- A ratio/average-per/growth/projection question that the data "
            "does not hold as a ready column = numbers steps for each raw "
            "figure, then ONE calculate step. The calculate step adds "
            '"function" and "inputs": each input is a {step N} placeholder '
            "or a plain number given in the question (like an assumed "
            "percent). Example: average basket = step 1 total sales "
            "(numbers), step 2 invoice count (numbers), step 3 lane "
            '"calculate", "function": "divide", "inputs": ["{step 1}", '
            '"{step 2}"], "waits_for": [1, 2].\n'
            "- Write each step's question in PLAIN BUSINESS LANGUAGE, the way "
            "a manager would ask it (e.g. \"What is supplier Acme's total?\"). NEVER "
            "name sheets, columns, operations or filters in it — each engine "
            "has its own catalog and chooses those itself. Use the catalog "
            "above only to decide the steps and lanes.\n"
            f"- Never more than {MAX_STEPS} steps.\n\n"
            "Reply with ONLY a JSON object (no prose, no code fences):\n"
            '{"steps": [{"question": "<focused question>", '
            '"lane": "numbers"|"text"|"calculate", '
            '"waits_for": [<earlier step numbers, or empty>], '
            '"function": "<calculate steps only>", '
            '"inputs": [<calculate steps only>]}]}\n\n'
            f"QUESTION: {q}"
        )
        raw = ask(prompt, purpose="planner").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[raw.find("{"): raw.rfind("}") + 1]
        steps = None
        try:
            steps = validate_plan(json.loads(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Planner reply unusable (%s): %r", exc, raw[:200])
        if steps is None:
            steps = fallback_plan(q)
        return {"plan": steps}

    return planner_node
