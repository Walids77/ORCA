# ORCA

**AI business assistant for retail, distribution, and operations teams** — an
agentic RAG system that reasons over documents + spreadsheets + images together
and returns exact numbers, citations, and business explanations.

> 🚧 **Status: early rebuild in progress.** This is the clean cloud rebuild of a
> working local prototype. Being built brain-first (agent orchestrator on
> LangGraph), tested locally, then deployed to AWS piece by piece.

## Roadmap
1. Local ingestion: a file → SQL rows + vectors + stored copy — **done ✅ (Excel · PDF prose · PDF number-tables→SQL · embedded photos)**
2. Agent brain (orchestrator) on LangGraph — **in progress 🚧** — the brain
   **plans**: a PLANNER writes a checklist (focused question · lane · waits-for),
   and a plan-runner executes it in capped parallel **waves** through the retrieval
   legs — dependency questions work ("which month was best → what did clients buy
   THAT month" = two waves, the answer flows between them). Three lanes: text
   retrieval · caged SQL (the LLM fills a form, code runs the query) · a caged
   **CALCULATE** worker (the LLM picks a whitelisted math function + which step
   answers feed it; code does the arithmetic — never LLM math). The plan is
   validated by code (real lanes, backward-only dependencies, step cap, safe
   fallback); the catalog carries a plain-English **meaning per sheet** so
   ambiguous business words map to the right table, and is filtered per user by
   code (permission-ready). Every LLM call metered (tokens + cost per answer).
   Temporary LLM: Gemini, swapping to Claude/Bedrock.
3. Heavy testing / eval harness in the terminal — retrieval **87.5%**; answer-level
   designs raced on one fixed mixed question set: **straight 9/13 → parallel 11/13
   (−28% latency) → router 11/13 (13/13 lane picks) → planner+waves 12/13, incl.
   the first full pass on a dependency question → after the calculate lane +
   catalog meanings + a data-cleaning round on the source workbook: floor 11/15,
   best run 15/15 → after the planner input fence + numbers-form stabilization
   (temperature 0 + worked examples + a list-dump guard): 15/15 repeated —
   including twice in a row on a store ingested through the human-in-the-loop
   gate, which then became the default Excel door** (repeated runs — an
   unreproducible pass counts for nothing);
   every eval recorded with a diagnosis trail, answer keys verified against the
   source file itself. Re-uploading a changed file first purges ALL its stored
   traces (SQL + vectors), then stores a clean copy.
4. Local web frontend (login · upload · ask)
5. AWS deployment (S3 · RDS + pgvector · Fargate · Cognito · Bedrock)

## How ingestion works (so far)
A file enters one **doorman** that detects its type by content and routes it to a
specialist. **Excel goes through the ingest GATE by default** (since Session 25):
a structure survey maps the sheet's real tables, headers, totals and hidden parts;
an LLM names each table's meaning from that map (never the raw cells); then one
gate decision — unreadable (stop and say why) · clarify (a short plain-English
question list the uploader answers once; the answers are remembered on the file's
**reading card** and reused on every re-upload) · all clear — and only then does
the workbook become three linked stores:
**SQL** (exact numbers, one typed table per sheet), **vectors** (semantic search over
each row), and a **raw file copy + manifest** — every record carries a pointer home
(sheet + row) for citations and a content hash for cheap incremental re-uploads.

The **PDF** specialist uses [Docling](https://github.com/docling-project/docling)
(layout-aware) to extract text and tables. Prose is split into **structure-aware,
heading-grouped chunks** (~500 tokens, ~12% overlap) — each chunk tagged with its
section, page, and document title for citations — then embedded for semantic search.
Number-tables (invoices, orders) are stitched back together across pages, typed
("$1,234.56" → 1234.56), and routed to SQL like Excel — proven against a real
order PDF (the items re-summed to the document's own printed total, to the cent).

**Photos embedded in a spreadsheet** (product catalogs, stock lists, orders) are
extracted from the workbook's own drawing layer — **every format, including the
old WMF/EMF ones most tools silently drop** (on one real stock file that was 57
of 100 photos) — tagged to the data row each one belongs to (by measured overlap;
a photo sitting equally on two rows is flagged for confirmation, never guessed),
captioned once by a vision model ("three metallic bangles in gold, rose gold,
and silver"), and stored so both questions work: *"show me the image of item
X"* (exact row lookup) and *"the black bracelet with the gold charm"* (meaning
search over captions). Every vision call is token-metered.

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
