# ORCA

**AI business assistant for retail, distribution, and operations teams** — an
agentic RAG system that reasons over documents + spreadsheets + images together
and returns exact numbers, citations, and business explanations.

> 🚧 **Status: early rebuild in progress.** This is the clean cloud rebuild of a
> working local prototype. Being built brain-first (agent orchestrator on
> LangGraph), tested locally, then deployed to AWS piece by piece.

## Roadmap
1. Local ingestion: a file → SQL rows + vectors + stored copy — **Excel done ✅ · PDF prose done ✅ · PDF number-tables next**
2. Agent brain (orchestrator) on LangGraph
3. Heavy testing / eval harness in the terminal (incl. retrieval accuracy)
4. Local web frontend (login · upload · ask)
5. AWS deployment (S3 · RDS + pgvector · Fargate · Cognito · Bedrock)

## How ingestion works (so far)
A file enters one **doorman** that detects its type by content and routes it to a
specialist. The Excel specialist turns a workbook into three linked stores:
**SQL** (exact numbers, one typed table per sheet), **vectors** (semantic search over
each row), and a **raw file copy + manifest** — every record carries a pointer home
(sheet + row) for citations and a content hash for cheap incremental re-uploads.

The **PDF** specialist uses [Docling](https://github.com/docling-project/docling)
(layout-aware) to extract text and tables. Prose is split into **structure-aware,
heading-grouped chunks** (~500 tokens, ~12% overlap) — each chunk tagged with its
section, page, and document title for citations — then embedded for semantic search.
Number-tables (invoices, orders) route to SQL like Excel (next build step).

## Setup / run (local)
ORCA runs in its own virtual environment so its packages never disturb your global
Python.

```bash
python -m venv .venv                       # create the sealed environment
.venv\Scripts\activate                     # activate it (Windows)
pip install -r requirements.txt            # install ORCA's dependencies

# try the PDF extractor on a file:
python -m orca.ingest.pdf_processor "data/your-file.pdf"
```

> First PDF run downloads Docling's layout/OCR models (~300 MB) once, then caches them.
> Put local test files in `data/` (git-ignored — never committed).

## How this was built
**Designed and directed by Walid Semaan — the system designer.** Walid defines the
architecture and creates the logic, brings his own research, and drives every decision.
The working method: Claude Code (AI) suggests options and implements the chosen approach
in code; Walid reviews the options and picks the direction, tests each result, and makes
the final call on the product. In short — **Walid designs the system and owns the
decisions; the AI writes the code under his direction and review.**
