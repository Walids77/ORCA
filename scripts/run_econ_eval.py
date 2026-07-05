"""Held-out validation eval: run the WINNING config (hybrid + BM25, RRF C=5) on a
NEW document (Introduction to Economics module) with its OWN 20 known-answer
questions. Tests whether the C=5 setting generalizes beyond the survey it was
tuned on.

Same rubric as the survey eval: did the right chunk land in the top-5?

    ./.venv/Scripts/python.exe scripts/run_econ_eval.py
"""
import sys, logging
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from orca.stores.vector_store import VectorStore
from orca.stores.hybrid import HybridSearcher

STORE = "data/stores/chroma"
COMPANY, FILE_ID = "demo", "econ_intro"
RRF_C = 5   # the winning setting from the survey eval

# (id, question, expected topic/section) — expected is for grading, not retrieval.
QUESTIONS = [
    # --- MICRO content (Ch 1-5) ---
    ("E1", "What is the definition of economics?", "Ch1 §1.1 definition"),
    ("E2", "What is opportunity cost?", "Ch1 scarcity/choice/opp cost"),
    ("E3", "What is the Production Possibilities Frontier?", "Ch1 PPF"),
    ("E4", "What are the determinants of demand?", "Ch2 §2.1.2 determinants of demand"),
    ("E5", "What is price elasticity of demand?", "Ch2 §2.1.3 elasticity"),
    ("E6", "How is market equilibrium determined?", "Ch2 §2.3 market equilibrium"),
    ("E7", "What are the assumptions of a perfectly competitive market?", "Ch5 §5.2.1"),
    ("E8", "What are the characteristics of a monopoly market?", "Ch5 §5.3 monopoly"),
    ("E9", "What is the law of variable proportions?", "Ch4 §4.1.4"),
    # --- MACRO content (Ch 6) ---
    ("E10", "What are the goals of macroeconomics?", "Ch6 §6.2 goals"),
    ("E11", "What are the approaches to measure national income (GDP/GNP)?", "Ch6 §6.2.1"),
    ("E12", "What is the difference between nominal and real GDP?", "Ch6 §6.3"),
    ("E13", "What is the GDP deflator and the Consumer Price Index (CPI)?", "Ch6 §6.4"),
    ("E14", "What is the business cycle?", "Ch6 §6.5 business cycle"),
    ("E15", "What is inflation and what are its causes?", "Ch6 §6.6.2 inflation"),
    # --- MULTI / compare ---
    ("E16", "What is the difference between monetary policy and fiscal policy?", "Ch6 §6.7.1/6.7.2"),
    # --- METADATA ---
    ("M17", "What is the title of this document?", "front matter p1"),
    ("M18", "In what month and year was this module published?", "front matter (Sept 2019)"),
    # --- TRAPS (not in the document) ---
    ("T19", "What does the document say about cryptocurrency or Bitcoin?", "NOT IN DOC"),
    ("T20", "What machine-learning models does the document use to forecast inflation?", "NOT IN DOC"),
]

store = VectorStore(path=STORE)
hybrid = HybridSearcher(store, company_id=COMPANY, file_id=FILE_ID)
print(f"Econ chunks in store: {len(hybrid.chunks)}  |  RRF C={RRF_C}\n" + "=" * 78)


def safe(s):
    return str(s).encode("ascii", "replace").decode()


for qid, q, expected in QUESTIONS:
    hits = hybrid.search(q, k=5, rrf_c=RRF_C)
    print(f"\n### {qid}  expected: {expected}")
    print(f"Q: {safe(q)}")
    for i, h in enumerate(hits, 1):
        m = h["metadata"]
        sec = safe(m.get("section", ""))[:40]
        snip = safe(h["text"].replace("\n", " "))[:110]
        print(f"  [{i}] p{m.get('page')} | {sec}")
        print(f"       {snip}")
