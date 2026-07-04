"""Retrieval eval: run the 20 known-answer questions against the embedded survey.

Pre-brain, so this grades RETRIEVAL (did the right chunk come back in the top-k?),
which is exactly the survey's #1 bottleneck. No LLM answer-writer yet — the
"retrieved answer" is what the top chunks actually contain.

    ./.venv/Scripts/python.exe scripts/run_retrieval_eval.py
"""
import sys, logging
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from orca.stores.vector_store import VectorStore

STORE = "data/stores/chroma"
COMPANY, FILE_ID = "demo", "agentic_rag_survey"

# (id, question, expected_page(s) note) — expected page is for MY grading, not shown to retrieval
QUESTIONS = [
    ("A1", "What is Naive RAG?", "p4"),
    ("A2", "What are the three core components of a RAG system?", "p3"),
    ("A3", "What are the four agentic design patterns?", "p9-11/abstract"),
    ("A4", "How does Modular RAG differ from Naive RAG?", "p5"),
    ("A5", "What is Agentic Corrective RAG?", "p19-21"),
    ("A6", "Name three agentic workflow patterns.", "p11-14"),
    ("A7", "What is the primary bottleneck in RAG quality?", "p33"),
    ("A8", "What tools and frameworks does the paper list for building Agentic RAG?", "p31"),
    ("A9", "Which application domains does the paper cover?", "p29-31"),
    ("A10", "What are the taxonomy categories of Agentic RAG systems?", "p14-28"),
    ("B11", "Who are the authors of this paper?", "p1"),
    ("B12", "What is the title of the paper?", "p1"),
    ("B13", "On which page does the Agentic RAG paradigm appear?", "p6"),
    ("B14", "Is there a GitHub repository, and what is it?", "p1"),
    ("B15", "How many categories are in the taxonomy of Agentic RAG systems?", "p14 (7)"),
    ("C16", "What accuracy did Agentic RAG achieve on the HumanEval coding benchmark?", "NOT IN DOC"),
    ("C17", "What does the paper recommend for fine-tuning or RLHF training of the LLM?", "NOT IN DOC"),
    ("C18", "What GPU hardware and pricing does the paper recommend for deployment?", "NOT IN DOC"),
    ("D19", "Compare Traditional RAG and Agentic RAG on context maintenance and adaptability.", "p29 table2"),
    ("D20", "What is the difference between Naive RAG and Advanced RAG?", "p4"),
]

store = VectorStore(path=STORE)
print(f"Collection size: {store.count()} chunks\n" + "=" * 70)

for qid, q, expected in QUESTIONS:
    hits = store.search(q, company_id=COMPANY, file_id=FILE_ID, k=5)
    print(f"\n### {qid}  (expected: {expected})")
    print(f"Q: {q}")
    for i, h in enumerate(hits, 1):
        m = h["metadata"]
        snippet = h["text"].replace("\n", " ")[:220]
        print(f"  [{i}] dist={h['distance']:.3f} | p{m.get('page')} | {m.get('section','')[:40]}")
        print(f"       {snippet}")
