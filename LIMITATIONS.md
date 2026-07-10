# ORCA — Known Limitations

> Honest list of what ORCA does NOT do well yet. Each item says the limit, why it
> happens, and the planned fix. Closed items are removed (not archived).

## Ingestion

- **Visual / image-heavy PDF catalogs extract only partially.** On a real product
  catalog (`品牌`, 37 pages, mixed Chinese/English), Docling rebuilt page 1 into a
  clean table but pages 2–3 fragmented into loose text scraps. Cause: free-form,
  photo-heavy grids without clear table lines. Nothing is lost (codes/prices remain
  as searchable text), but those pages don't become clean SQL tables.
  *Fix path:* stronger table mode / OCR settings, and the Claude-oracle method
  (compare against the chatbot) — eval-graded, later.

## The brain

- **No arithmetic.** ORCA retrieves and aggregates (SUM/AVG/COUNT...) but cannot
  COMPUTE across results: "average basket = total sales ÷ total invoices" wrote a
  perfect 3-step plan in the Session-15 eval — and stopped at the divide, because
  no divide engine exists (and LLM mental math is banned by design). *Fix path
  (Session 16, locked):* the caged CALCULATE worker — a whitelist of tested math
  functions the plan can call; our code does the math, never the LLM.

- **The catalog knows sheet NAMES, not MEANINGS.** "What was bought in December?"
  was answered from the Expenses sheet (company spending) instead of the Sales
  remarks (client purchases) — ambiguous business words map to the wrong table
  with full confidence. *Fix path (Session 16, locked):* a one-line plain-English
  meaning per sheet in the catalog (the Session-11 design; pairs with agreed
  benchmarks later).

- **Plans are 2D only (no branching plans).** The planner writes the whole
  checklist upfront; a question whose NEXT step depends on an intermediate answer
  ("if growth is under 10%, investigate X; otherwise Y") can't be planned yet.
  *Fix path (parked, recorded):* the conditional / re-planner level — the plan
  revises itself between waves.

- **No conversation memory yet** — each question stands alone; "and compare it to
  last year?" is meaningless. *Fix path:* LangGraph checkpointing (brief #16).

## Retrieval

- **One fragile fact can flip with question phrasing.** The survey's "primary
  bottleneck" answer passes under some sub-question wordings and fails under
  others in the SAME code (Session-15: passed as a direct question, failed
  inside the cross-corpus compound question) — whole-corpus top-5 crowding.
  *Fix path:* retrieval precision (raise k / a reranker once Bedrock unblocks),
  eval-graded; stability testing (repeated runs) per the no-lucky-passes rule.

- **LIST answers cap at 40 rows** (raised from 20 in Session 15 when LIST became
  the month-detail engine). A period holding more rows than the cap would
  truncate silently. *Fix path:* aggregate or paginate when a real case hits it.

## Cost / scale

- **The data catalog rides inside two prompts** (router + numbers form), so
  per-question token cost grows with the tenant's data. Fine at demo size;
  *fix path:* catalog summarization or caching when the corpus grows.

## Testing / ops (owed, tracked in `ORCA_BRIEF.md`)

- **No automated test suite / CI gate yet** — the pre-push checklist is run by
  hand; evals are recorded (`eval/`) but launched manually.
- **No step-level tracing yet** (Langfuse/Phoenix, brief #17) — the token/cost
  meter (item #20, done) covers spend, not full traces.
