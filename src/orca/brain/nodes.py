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
from orca.stores.hybrid import HybridSearcher
from orca.stores.sql_store import SqlStore


# ── Leg 1 + 2: TEXT (meaning + keyword, already fused inside HybridSearcher) ──
def make_search_text_node(searcher: HybridSearcher, k: int = 5):
    def search_text_node(notebook: Notebook) -> dict:
        hits = searcher.search(notebook["question"], k=k)
        return {"text_hits": hits}

    return search_text_node


# ── Leg 3: NUMBERS (the exact-number SQL store) ──
# On this straight skeleton we don't yet let an LLM write SQL (that's a later
# branch). We just surface WHICH exact-number tables exist, so the combine step
# knows what could be asked. This proves the leg is wired to the real SQL store.
def make_list_numbers_node(sql: SqlStore):
    def list_numbers_node(notebook: Notebook) -> dict:
        tables = [dict(row) for row in sql.catalog()]
        return {"number_tables": tables}

    return list_numbers_node


# ── COMBINE (Step 1 = plain stitch, NO AI yet) ──
def plain_combine_node(notebook: Notebook) -> dict:
    hits = notebook.get("text_hits", [])
    tables = notebook.get("number_tables", [])

    lines = [f"Question: {notebook['question']}", ""]
    lines.append(f"Found {len(hits)} text passage(s):")
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata", {})
        where = f"p{meta.get('page')} | {str(meta.get('section', '') or '')[:40]}"
        preview = " ".join(h.get("text", "").split())[:140]
        lines.append(f"  {i}. [{where}] {preview}...")

    lines.append("")
    lines.append(f"Exact-number tables available: {len(tables)}")
    for t in tables:
        lines.append(f"  - {t.get('sheet')} ({t.get('row_count')} rows)")

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

    prompt = (
        "You are ORCA, a business document assistant. Answer the question using "
        "ONLY the passages below. If the answer is not in them, reply exactly: "
        "\"I can't answer that from the uploaded documents.\" "
        "Cite the passage numbers you used, like [1] or [2].\n\n"
        f"QUESTION: {notebook['question']}\n\n"
        f"PASSAGES:\n{evidence}"
    )
    return {"answer": ask(prompt)}
