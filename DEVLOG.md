# ORCA — Development Log

> Newest entry first. One dated entry per work session.

## 2026-07-05 — Session 6: hybrid BM25 retrieval + RRF C-tuning → 43% to 82.5% (embedder unchanged)
- **Bedrock still blocked.** Re-checked a day after the Paid-Plan upgrade: on-demand quota
  still 0 for EVERY model (not just Titan). Ran a **ground-truth terminal test** (one Titan
  `invoke_model`) → `ThrottlingException` (not AccessDenied) = our code/creds/region are
  correct; only AWS's account-level quota is missing. Confirmed the account is genuinely Paid
  (real USD billing). **Opened a free AWS Support case `178327435100356`** to enable on-demand.
- **Walid's call:** the replacement embedder must run on AWS — no local model. So we advanced
  the embedder-INDEPENDENT retrieval lever instead.
- **Built hybrid retrieval** (`src/orca/stores/hybrid.py`): BM25 **keyword search** (`rank_bm25`)
  run alongside the existing meaning search, the two ranked lists fused with **RRF**. Added
  chunk `id` to `vector_store.search` + an `all_chunks()` helper.
- **Eval-proven on the survey** (same 20-Q rubric): vector-only **43%** → hybrid **72.5%**.
  Wins = exact-word / section-title questions (Corrective RAG, Tools & Frameworks, Modular…).
- **Found + fixed a merge bug:** the title/authors chunk is BM25 rank 1 but vector rank 43 —
  strong in ONE list only — and the standard RRF setting (`C=60`) buried it. **Lowering C to 5**
  makes a strong single-list hit surface → rescued authors/title/bottleneck → **82.5%**.
- **Validated C=5 on a held-out doc** (downloaded a 110-page "Introduction to Economics"
  module, micro + macro; fresh 20 questions): **18/18 answerable + 2/2 traps ≈ 100%**, and
  C=5 cost nothing vs C=60. → **adopted C=5 as the default.** Overfitting fear did not
  materialize. Details: `eval/pdf_retrieval_hybrid_2026-07-05.md`, `eval/econ_retrieval_validation_2026-07-05.md`.
- **Next:** check the AWS case → Titan embedder eval on top of 82.5%; model-free meanwhile =
  metadata route + keep footnotes (GitHub-link miss); then reranker/enrichment (need a model).

## 2026-07-05 — Session 4: retrieval eval (baseline 43%) + captions/tables embedding + Bedrock wiring
- **Embed more than prose** (`ingest/records.py`): now KEEP captions (tagged
  `[Figure/Table caption]` — the cheap way to make diagrams searchable) and EMBED every
  table as text (`col: value; …` rows, own chunk, cited to its page). Clarified the 3
  content types: number-table → SQL · word-table → text · figure/photo → caption now
  (vision later); a picture has no structure, so it never goes to SQL.
- **Embedded the FULL 42-page survey** (Session 3 was only an 8-page peek) into a persistent
  Chroma store at `data/stores/chroma` (git-ignored). 169 chunks (160 prose · 8 table ·
  27 caption · 1 front-matter). The 27 captions would've been dropped before.
- **Built the retrieval eval** (`scripts/run_retrieval_eval.py`): 20 known-answer questions
  across content · metadata · "not-in-doc" traps · multi-part. Ground truth read from the
  paper. **Baseline = 8.5/20 (43%)**, graded at retrieval level (right chunk in top-5?),
  since the LLM answer-writer isn't built yet. Saved to `eval/pdf_retrieval_baseline_2026-07-04.md`.
- **Diagnosis (the point of the number):** "magnet chunks" (a few generic sections match
  everything), titled sections that ARE the answer got missed (A7 §10.3, A8 §8), all 5
  metadata questions failed. → validates hybrid BM25 (#15) + a better embedder — two levers
  for two different failures (eval decides the combination; research says don't stack blindly).
- **Read the full survey → saved insights** (`memory/agentic_rag_survey_insights.md`): its
  §4 workflow patterns = the industry names for Walid's 2D-decomposition; §5.5 Adaptive =
  recipe for the complexity router; §8 validates the LangGraph+Bedrock stack; §10.3 =
  "retrieval quality is the bottleneck" (validates doing this eval now).
- **Started the Bedrock/Titan swap:** installed `boto3`; credentials + admin + region + code
  all verified working (a `ThrottlingException` proved the call reaches Titan). **Blocked by
  the account being on the AWS Free Plan**, which fences off Bedrock on-demand (quota 0,
  "not adjustable"). Real fix = **upgrade to the Paid Plan** (credits carry over, still ~free;
  needed for RDS/S3/Fargate anyway). Full detail in `memory/aws_bedrock_setup.md`.
- **Next session:** upgrade AWS → Paid Plan → re-test Titan → if working, run the embedder
  eval **with Titan** (Walid's pick over a local model) and compare vs the 43% baseline; then
  hybrid BM25. After retrieval is solid: PDF number-tables → SQL tidy, then the agent brain.

## 2026-07-04 — Session 3: PDF ingestion — extractor + prose chunker + end-to-end retrieval
- **Housekeeping first:** gave ORCA its own **virtualenv** (`.venv`, git-ignored); all
  deps now install into the box → ORCA can no longer disturb global Python. Added
  `docling` to `requirements.txt`.
- **Research-first:** checked 2026 best practice for PDF/OCR extraction + chunking —
  structure-aware ~500-token chunks + ~12% overlap + hierarchical (parent-child) +
  metadata per chunk; tables are the hardest element; layout-aware parsing matters.
- **PDF extractor** (`ingest/pdf_processor.py`): chose **Docling** (open-source,
  layout-aware) over old ORCA's 3 glued libraries. Returns a `PdfExtract` = tables (grids
  + page) + labelled text blocks + page numbers + markdown. `max_pages` via `page_range`.
- **Tested on 4 real PDFs:** salary slip + CV clean; PO = 7 page-tables (numbers present,
  headers inconsistent → table-tidy work); catalog (品牌, 37p, mixed-language) = page 1 a
  clean table, pages 2–3 fragmented (the hard case, to eval/improve later).
- **Prose chunker** (`ingest/records.py::build_pdf_chunks`): our own transparent code —
  heading-grouped, ~500 tokens, ~12% overlap, splits oversized blocks on sentences, never
  crosses a heading. Metadata card per chunk: `section`, `section_page`, `doc_title`,
  `parent_id` (hierarchical-ready), `page`. Docling's HybridChunker kept for a later eval.
- **Fixed a real bug:** authors were becoming fake one-line "sections" (Docling tags author
  names as headers). New rule groups the title + all authors into ONE front-matter chunk
  (front matter = everything before the first real heading); also records which page each
  chapter starts on (`section_page`) so "which page is chapter X?" is answerable.
- **End-to-end milestone** (public test file `data/agentic_rag_survey.pdf`, arXiv 2501.09136):
  extract → embed (MiniLM/Chroma, via new `vector_store.store_pdf`) → query. **3/4 questions
  dead-on** with section + page citations.
- **Lesson logged:** pure semantic search is weak on *metadata* questions ("who are the
  authors?") — the author chunk ranked ~4th, still inside top-5 so an answer step recovers
  it; clean fixes are already on the roadmap (hybrid BM25 #15, Titan embedder = an eval case).
- **Decision confirmed:** swapping the embedder later won't change the extract/chunk/metadata
  logic — the embedder is a swappable plug; a swap = re-embed + maybe re-tune chunk size.
- **Next session:** build the **retrieval-accuracy eval** (known-answer scorecard, include the
  author case), then the **table→SQL tidy** stage (headers across pages, number typing, total-row
  flagging — reuses the Excel logic).

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
