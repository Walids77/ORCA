"""The stations (nodes) on ORCA's straight road.

Each node is a plain function: it receives the whole Notebook and returns ONLY
the new entries it adds. The real retrieval engines are passed in from graph.py
so the nodes stay easy to test and the wiring lives in one place.

Step 1 (this version): all three legs are REAL, but the final COMBINE is a plain
non-AI stitch — it just gathers what the legs found. The real Gemini thinking
node replaces it in Step 2.
"""

import json

from orca.brain.state import Notebook
from orca.brain.llm import ask
from orca.brain.numbers import load_catalog, catalog_text, plan_query, run_plan, result_text
from orca.stores.hybrid import HybridSearcher
from orca.stores.sql_store import SqlStore


# ── ROUTER (Session 14): pick the lane(s) + split compound questions ──
# Reads the tenant's data catalog (Walid's Session-10 rule: domain-first) and
# fills a small form: lane = text / numbers / both, plus a FOCUSED sub-question
# per chosen leg. Splitting is the real fix the run-1/run-2 evidence demanded —
# the one-shot numbers form coin-flips when the question carries a text half.
# If the reply is unreadable we fall back to "both" (= the parallel design):
# the router may only ever SAVE work, never lose an answer to a parse error.
def make_router_node(menu: str, doc_list: str):
    def router_node(notebook: Notebook) -> dict:
        q = notebook["question"]
        prompt = (
            "You are the ROUTER for a business data assistant. Decide which "
            "engine(s) can answer the user's question:\n"
            '- "numbers": computed from the spreadsheet data below (sums, '
            "averages, counts, rankings, lists of matching rows).\n"
            '- "text": found by READING the text documents below (definitions, '
            "explanations, remarks, policies — no computation).\n"
            '- "both": needs an exact computed figure AND explanation/context '
            "from the text.\n\n"
            f"SPREADSHEET CATALOG:\n{menu}\n\n"
            f"TEXT DOCUMENTS SEARCHABLE:\n{doc_list}\n"
            "(The spreadsheets' free-text remark columns are searchable as "
            "text too.)\n\n"
            "Reply with ONLY a JSON object (no prose, no code fences):\n"
            '{"lane": "text"|"numbers"|"both", '
            '"numbers_question": "<a single plain question asking ONLY for the '
            'figure/rows to compute — strip any explanation part>", '
            '"text_question": "<what to look up in the text — strip any '
            'computation part>"}\n'
            "Include numbers_question when lane is numbers/both, text_question "
            "when lane is text/both. If the question has two halves, each "
            "sub-question carries ONLY its own half.\n\n"
            f"QUESTION: {q}"
        )
        raw = ask(prompt, purpose="router").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[raw.find("{"): raw.rfind("}") + 1]
        try:
            plan = json.loads(raw)
            lane = plan.get("lane")
            if lane not in ("text", "numbers", "both"):
                raise ValueError(f"bad lane {lane!r}")
        except Exception:
            plan, lane = {}, "both"    # safe fallback = run everything
        return {
            "lane": lane,
            "text_question": str(plan.get("text_question") or q),
            "numbers_question": str(plan.get("numbers_question") or q),
        }

    return router_node


# ── Leg 1 + 2: TEXT (meaning + keyword, already fused inside HybridSearcher) ──
def make_search_text_node(searcher: HybridSearcher, k: int = 5):
    def search_text_node(notebook: Notebook) -> dict:
        # The router may have written a focused sub-question; without a router
        # (straight/parallel designs) we search the full question as before.
        query = notebook.get("text_question") or notebook["question"]
        hits = searcher.search(query, k=k)
        return {"text_hits": hits}

    return search_text_node


# ── Leg 3: NUMBERS (the exact-number SQL store) ──
# Session 13: the leg now ANSWERS instead of just listing tables. Two moves
# (see numbers.py): the LLM fills a structured form (which sheet / operation /
# column / filters) — MOVE 1 — and our validated code builds + runs the SQL
# itself — MOVE 2. The LLM never writes SQL.
def make_answer_numbers_node(sql: SqlStore, company_id: str,
                             allowed_files: set[str] | None = None):
    # allowed_files = the RBAC fence: the planner's menu only ever contains
    # sheets from files this user may see (None = everything, today's default).
    catalog = load_catalog(sql, company_id, allowed_files)
    menu = catalog_text(catalog)

    def answer_numbers_node(notebook: Notebook) -> dict:
        # Focused sub-question from the router when present, else the original.
        question = notebook.get("numbers_question") or notebook["question"]
        plan = plan_query(question, menu)
        result = run_plan(sql, catalog, plan)
        return {"number_result": result}

    return answer_numbers_node


# ── COMBINE (Step 1 = plain stitch, NO AI yet) ──
def plain_combine_node(notebook: Notebook) -> dict:
    hits = notebook.get("text_hits", [])

    lines = [f"Question: {notebook['question']}", ""]
    lines.append(f"Found {len(hits)} text passage(s):")
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata", {})
        where = f"p{meta.get('page')} | {str(meta.get('section', '') or '')[:40]}"
        preview = " ".join(h.get("text", "").split())[:140]
        lines.append(f"  {i}. [{where}] {preview}...")

    numbers = result_text(notebook.get("number_result", {}))
    if numbers:
        lines += ["", "Exact numbers:", numbers]

    return {"answer": "\n".join(lines)}


# ── COMBINE (Step 2 = the real thinking node, powered by the LLM adapter) ──
# It reads the retrieved passages and answers ONLY from them. If the passages
# don't contain the answer, it must say so — this is the anti-hallucination
# guardrail that the plain stitch could never do.
def llm_combine_node(notebook: Notebook) -> dict:
    hits = notebook.get("text_hits", [])

    # Build the evidence block: each passage with its page + section, so the
    # model can cite where the answer came from.
    passages = []
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata", {})
        where = f"page {meta.get('page')}, section {meta.get('section', '?')}"
        passages.append(f"[{i}] ({where})\n{h.get('text', '')}")
    evidence = "\n\n".join(passages) if passages else "(no passages retrieved)"

    # Session 13: the numbers leg's computed result rides along as its own
    # evidence block. These figures were computed by a database query, never by
    # an LLM — the answer-writer must use them verbatim, cited as [numbers].
    numbers = result_text(notebook.get("number_result", {}))
    numbers_block = (
        f"\n\nEXACT NUMBERS (computed directly from the company's spreadsheet "
        f"data by a database query — use these figures VERBATIM, cite as "
        f"[numbers]):\n{numbers}" if numbers else ""
    )

    prompt = (
        "You are ORCA, a business document assistant. Answer the question using "
        "ONLY the passages and the EXACT NUMBERS block below. If the answer is "
        "in neither, reply exactly: "
        "\"I can't answer that from the uploaded documents.\" "
        "Never compute or estimate figures yourself — only repeat figures from "
        "the EXACT NUMBERS block. Cite the passage numbers you used, like [1] "
        "or [2], and cite computed figures as [numbers].\n\n"
        f"QUESTION: {notebook['question']}\n\n"
        f"PASSAGES:\n{evidence}"
        f"{numbers_block}"
    )
    return {"answer": ask(prompt, purpose="combine")}


# ── COMBINE for the PLANNER design (Session 15) ──
# Same rules, different evidence shape: the plan-runner leaves one result per
# checklist step in the notebook. Text-step passages get one global numbering
# (for [1]-style citations); each numbers step contributes its own computed
# block, labelled with the step's focused question so the answer-writer knows
# which figure answers which part.
def plan_combine_node(notebook: Notebook) -> dict:
    passages, numbers_blocks = [], []
    for n in sorted(notebook.get("step_results", {})):
        res = notebook["step_results"][n]
        if res.get("lane") == "text":
            for h in res.get("hits", []):
                meta = h.get("metadata", {})
                where = f"page {meta.get('page')}, section {meta.get('section', '?')}"
                passages.append(f"[{len(passages) + 1}] ({where})\n{h.get('text', '')}")
        else:
            block = result_text(res.get("result", {}))
            if block:
                numbers_blocks.append(f"(step {n}: {res.get('question', '')})\n{block}")

    evidence = "\n\n".join(passages) if passages else "(no passages retrieved)"
    numbers_block = (
        "\n\nEXACT NUMBERS (computed directly from the company's spreadsheet "
        "data by database queries — use these figures VERBATIM, cite as "
        "[numbers]):\n" + "\n\n".join(numbers_blocks) if numbers_blocks else ""
    )
    # Session-15 eval lesson: on multi-part questions the all-or-nothing rule
    # made the combine refuse EVERYTHING when one part was missing — so this
    # combine must answer the parts it has and name the part it can't.
    prompt = (
        "You are ORCA, a business document assistant. Answer the question using "
        "ONLY the passages and the EXACT NUMBERS block below. If NONE of it "
        "answers the question, reply exactly: "
        "\"I can't answer that from the uploaded documents.\" "
        "If the evidence answers only PART of a multi-part question, answer "
        "that part fully and state plainly which part the uploaded documents "
        "cannot answer — never refuse everything when a part is answerable. "
        "Never compute or estimate figures yourself — only repeat figures from "
        "the EXACT NUMBERS block. Cite the passage numbers you used, like [1] "
        "or [2], and cite computed figures as [numbers].\n\n"
        f"QUESTION: {notebook['question']}\n\n"
        f"PASSAGES:\n{evidence}"
        f"{numbers_block}"
    )
    return {"answer": ask(prompt, purpose="combine")}
