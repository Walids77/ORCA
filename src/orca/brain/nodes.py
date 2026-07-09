"""The stations (nodes) on ORCA's straight road.

Each node is a plain function: it receives the whole Notebook and returns ONLY
the new entries it adds. The real retrieval engines are passed in from graph.py
so the nodes stay easy to test and the wiring lives in one place.

Step 1 (this version): all three legs are REAL, but the final COMBINE is a plain
non-AI stitch — it just gathers what the legs found. The real Gemini thinking
node replaces it in Step 2.
"""

from orca.brain.state import Notebook
from orca.brain.llm import ask
from orca.brain.numbers import load_catalog, catalog_text, plan_query, run_plan, result_text
from orca.stores.hybrid import HybridSearcher
from orca.stores.sql_store import SqlStore


# ── Leg 1 + 2: TEXT (meaning + keyword, already fused inside HybridSearcher) ──
def make_search_text_node(searcher: HybridSearcher, k: int = 5):
    def search_text_node(notebook: Notebook) -> dict:
        hits = searcher.search(notebook["question"], k=k)
        return {"text_hits": hits}

    return search_text_node


# ── Leg 3: NUMBERS (the exact-number SQL store) ──
# Session 13: the leg now ANSWERS instead of just listing tables. Two moves
# (see numbers.py): the LLM fills a structured form (which sheet / operation /
# column / filters) — MOVE 1 — and our validated code builds + runs the SQL
# itself — MOVE 2. The LLM never writes SQL.
def make_answer_numbers_node(sql: SqlStore, company_id: str):
    catalog = load_catalog(sql, company_id)
    menu = catalog_text(catalog)

    def answer_numbers_node(notebook: Notebook) -> dict:
        plan = plan_query(notebook["question"], menu)
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
    return {"answer": ask(prompt)}
