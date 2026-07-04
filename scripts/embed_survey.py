"""Embed the FULL Agentic RAG survey (all 42 pages) into ORCA's local vector store.

This is the baseline knowledge base for the retrieval eval. Run once:
    ./.venv/Scripts/python.exe scripts/embed_survey.py

Slow part is Docling extraction (~15s/page on CPU → ~10 min for 42 pages).
Embedding is the free local MiniLM model. Store persists at data/stores/chroma.
"""
import sys
import time
import logging

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from orca.ingest.pdf_processor import extract_pdf
from orca.stores.vector_store import VectorStore

PDF = "data/agentic_rag_survey.pdf"
STORE = "data/stores/chroma"
COMPANY = "demo"
FILE_ID = "agentic_rag_survey"

t0 = time.time()
print(f"Extracting FULL PDF (no page cap): {PDF}")
extract = extract_pdf(PDF)  # no max_pages -> all 42 pages
print(f"Extracted: {extract.page_count} pages, {len(extract.tables)} tables, "
      f"{len(extract.text_blocks)} text blocks  ({time.time()-t0:.0f}s)")

store = VectorStore(path=STORE)
n = store.store_pdf(company_id=COMPANY, file_id=FILE_ID, extract=extract)

# breakdown so we can see tables/captions actually landed
from orca.ingest.records import build_pdf_chunks
chunks = build_pdf_chunks(extract, COMPANY, FILE_ID)
n_table = sum(1 for c in chunks if c["metadata"].get("is_table"))
n_caption = sum(1 for c in chunks if "[Figure/Table caption]" in c["text"])
n_front = sum(1 for c in chunks if c["metadata"].get("is_frontmatter"))
n_prose = len(chunks) - n_table - n_front

print("\n=== DONE ===")
print(f"Total chunks embedded : {n}")
print(f"  prose/section chunks: {n_prose}")
print(f"  table chunks        : {n_table}")
print(f"  caption chunks      : {n_caption}  (counted inside prose)")
print(f"  front-matter chunk  : {n_front}")
print(f"Store: {STORE}  |  collection total now: {store.count()}")
print(f"Total time: {time.time()-t0:.0f}s")
