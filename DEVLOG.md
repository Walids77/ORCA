# ORCA — Development Log

> Newest entry first. One dated entry per work session.

## 2026-07-04 — Session 2: Excel ingestion pipeline (doorman → 7 stages → 3 stores)
- **Doorman** (`ingest/router.py`): detects file type by real content (magic bytes),
  not just the extension, and routes to the right specialist. PDF/image are stubs.
- **Excel processor** (`ingest/excel_processor.py`), stages 1–5: open workbook →
  **block-detection** (a sheet can hold several tables; keeps a side "Fast Calculation"
  mini-table out of the main data by matching each block to the main column types) →
  typed read (dates/numbers/text; `NA`+blank → empty) → flag Total/summary rows →
  tag columns (meaning + aliases + measured data type).
- **Three stores** (stages 6–7): 📊 `stores/sql_store.py` — one typed SQLite table per
  sheet with tenant + citation + `row_hash` columns (exact `SUM` matched the sheet's own
  Total; re-upload doesn't duplicate). 📁 `stores/file_store.py` — raw copy + manifest +
  content hash (identical re-upload is skipped). 🧠 `stores/vector_store.py` — Chroma +
  local all-MiniLM embedder (967 chunks; meaning-search returns the right rows + citations).
- **Verified end-to-end on the real sample workbook** (6 sheets).
- **Decisions:** update strategy = upload-based + incremental (hash-diff, cheap SQL replace /
  costly-vector diff); embedder = local now → **Bedrock Titan V2** final (eval Titan vs
  Cohere-multilingual on the real mixed-language data); chunking = solid row-per-chunk V1,
  richer filterable metadata to be eval-graded later.
- **Known follow-up:** move ORCA into its own virtualenv (the Chroma install disturbed a
  couple of global packages).
- **Next session:** build the **PDF processor** (route + extract), then develop
  embedding/metadata/chunking and run a **retrieval-accuracy eval**.

## 2026-07-03 — Session 1: Clean repo skeleton + public GitHub launch
- Initialized the fresh git repository (branch `main`) — clean history, personal identity.
- Created the Python skeleton: `src/orca/` package, `tests/`, `README.md`, `requirements.txt`.
- Built the `.gitignore` privacy fence: secrets, planning/working notes, and the local
  `data/` folder are excluded from the public repo (verified before committing).
- First commit `2e025a5` pushed to the new public repo: **github.com/Walids77/ORCA**
  (🚧 under-construction description + roadmap README).
- Added `progress.html` — a visual done-so-far timeline + the phase A–E build plan.
- Prepared `data/` (git-ignored) and received the first sample Excel for ingestion testing.
- **Next session:** Phase A — review the Excel extractor from the old ORCA baseline
  (per-file approval: copy / rewrite / skip), then ingest the sample Excel into
  SQLite + ChromaDB locally.
