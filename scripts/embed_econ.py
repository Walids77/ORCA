"""Embed the full Introduction to Economics module into ORCA's local vector store.

Held-out validation document for the retrieval eval (covers BOTH micro + macro),
stored alongside the survey in the same Chroma collection but under its own
file_id so tenant filtering keeps them separate.

    ./.venv/Scripts/python.exe scripts/embed_econ.py
"""
import sys, time, logging
sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from orca.ingest.pdf_processor import extract_pdf
from orca.stores.vector_store import VectorStore
from orca.ingest.records import build_pdf_chunks

PDF = "data/econ_intro.pdf"
STORE = "data/stores/chroma"
COMPANY, FILE_ID = "demo", "econ_intro"

t0 = time.time()
print(f"Extracting FULL PDF: {PDF}")
extract = extract_pdf(PDF)   # all pages
print(f"Extracted: {extract.page_count} pages, {len(extract.tables)} tables, "
      f"{len(extract.text_blocks)} text blocks  ({time.time()-t0:.0f}s)")

store = VectorStore(path=STORE)
n = store.store_pdf(company_id=COMPANY, file_id=FILE_ID, extract=extract)

chunks = build_pdf_chunks(extract, COMPANY, FILE_ID)
n_table = sum(1 for c in chunks if c["metadata"].get("is_table"))
n_front = sum(1 for c in chunks if c["metadata"].get("is_frontmatter"))
print(f"\n=== DONE ===  chunks embedded: {n}  (tables {n_table}, front {n_front})")
print(f"Store: {STORE}  |  collection total now: {store.count()}")
print(f"Total time: {time.time()-t0:.0f}s")
