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

- **Dependency (depth) questions aren't answerable yet.** "Which month had the
  highest sales, and what did clients buy THAT month?" fails: the text half needs
  the number half's ANSWER before it can search, and today's router only picks
  lanes — it can't chain steps. Failed all 3 designs in the Session-14 eval, by
  design. *Fix path (Session 15, locked):* router→planner (a checklist with
  waits-for dependencies) + a capped plan-runner executing it in waves.

- **Compound questions depend on the router.** Without the router, the one-shot
  numbers form coin-flips on questions that mix a figure with an explanation
  (engaged in one eval run, declined in another). The router's question-splitting
  fixes this deterministically — so the router lane is now the production path.

- **No conversation memory yet** — each question stands alone; "and compare it to
  last year?" is meaningless. *Fix path:* LangGraph checkpointing (brief #16).

## Retrieval

- **Whole-corpus search can crowd out a niche document's chunk.** The survey's
  "primary bottleneck" question passed when search was pinned to the survey
  (Session 12) but fails consistently on the whole tenant corpus (Session 14) —
  the Excel's row-chunks compete for the top-5 spots. *Fix path:* retrieval
  precision (raise k / a reranker once Bedrock unblocks), eval-graded.

- **LIST answers cap at 20 rows.** A month-detail request ("everything sold in
  February" — ~37 rows) would truncate. *Fix path:* raise the cap or aggregate,
  when the depth branch makes LIST the month-detail engine (Session 15 eval).

## Cost / scale

- **The data catalog rides inside two prompts** (router + numbers form), so
  per-question token cost grows with the tenant's data. Fine at demo size;
  *fix path:* catalog summarization or caching when the corpus grows.

## Testing / ops (owed, tracked in `ORCA_BRIEF.md`)

- **No automated test suite / CI gate yet** — the pre-push checklist is run by
  hand; evals are recorded (`eval/`) but launched manually.
- **No step-level tracing yet** (Langfuse/Phoenix, brief #17) — the token/cost
  meter (item #20, done) covers spend, not full traces.
