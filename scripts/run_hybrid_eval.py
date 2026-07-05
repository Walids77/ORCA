"""Hybrid retrieval eval: vector-only vs vector+BM25 (RRF), same 20 known-answer Qs.

Prints, per question, the top-5 chunks from EACH method (page + section title) so we
can grade whether the right chunk now lands in the top-5 — graded by the same rubric
as the 43% baseline (eval/pdf_retrieval_baseline_2026-07-04.md).

    ./.venv/Scripts/python.exe scripts/run_hybrid_eval.py
"""
import sys, logging
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from orca.stores.vector_store import VectorStore
from orca.stores.hybrid import HybridSearcher

STORE = "data/stores/chroma"
COMPANY, FILE_ID = "demo", "agentic_rag_survey"

QUESTIONS = [
    ("A1", "What is Naive RAG?", "§2.3.1 p4"),
    ("A2", "What are the three core components of a RAG system?", "§2.2 p3"),
    ("A3", "What are the four agentic design patterns?", "§3 p9-11"),
    ("A4", "How does Modular RAG differ from Naive RAG?", "§2.3 p5"),
    ("A5", "What is Agentic Corrective RAG?", "§5.4 p19-21"),
    ("A6", "Name three agentic workflow patterns.", "§4 p11-14"),
    ("A7", "What is the primary bottleneck in RAG quality?", "§10.3 p33"),
    ("A8", "What tools and frameworks does the paper list for building Agentic RAG?", "§8 p31"),
    ("A9", "Which application domains does the paper cover?", "§7/§10.6"),
    ("A10", "What are the taxonomy categories of Agentic RAG systems?", "§5.2 p14-28"),
    ("B11", "Who are the authors of this paper?", "front-matter p1"),
    ("B12", "What is the title of the paper?", "front-matter p1"),
    ("B13", "On which page does the Agentic RAG paradigm appear?", "§2.3.5 p6"),
    ("B14", "Is there a GitHub repository, and what is it?", "footnote p1"),
    ("B15", "How many categories are in the taxonomy of Agentic RAG systems?", "§5.2 p14 (7)"),
    ("C16", "What accuracy did Agentic RAG achieve on the HumanEval coding benchmark?", "NOT IN DOC"),
    ("C17", "What does the paper recommend for fine-tuning or RLHF training of the LLM?", "NOT IN DOC"),
    ("C18", "What GPU hardware and pricing does the paper recommend for deployment?", "NOT IN DOC"),
    ("D19", "Compare Traditional RAG and Agentic RAG on context maintenance and adaptability.", "§9 table2 p29"),
    ("D20", "What is the difference between Naive RAG and Advanced RAG?", "§2.3.1/2 p4"),
]

store = VectorStore(path=STORE)
hybrid = HybridSearcher(store, company_id=COMPANY, file_id=FILE_ID)
print(f"Collection: {store.count()} chunks\n" + "=" * 78)


def fmt(hits):
    parts = []
    for h in hits:
        m = h["metadata"]
        sec = str(m.get("section", "") or "")[:30]
        parts.append(f"p{m.get('page')}|{sec}")
    return parts


for qid, q, expected in QUESTIONS:
    vec = store.search(q, company_id=COMPANY, file_id=FILE_ID, k=5)
    hyb = hybrid.search(q, k=5)
    print(f"\n### {qid}  expected: {expected}")
    print(f"Q: {q}")
    print("  VEC:")
    for t in fmt(vec):
        print(f"     {t}")
    print("  HYB:")
    for t in fmt(hyb):
        print(f"     {t}")
