# ORCA — Known Limitations

> Honest list of what ORCA does NOT do well yet. Each item says the limit, why it
> happens, and the planned fix. Closed items are removed (not archived).

## Ingestion

- **PDFs get no gate treatment yet.** The ingest gate (survey → clarifying
  questions → reading card) is the default door for **Excel only** (Session 25);
  a messy or scanned PDF is still ingested silently with no questions asked.
  *Fix path:* extend the gate idea to the PDF branch (quality scan + uploader
  questions) — a recorded future extension, eval-gated like everything else.

- **Visual / image-heavy PDF catalogs extract only partially.** On a real product
  catalog (`品牌`, 37 pages, mixed Chinese/English), Docling rebuilt page 1 into a
  clean table but pages 2–3 fragmented into loose text scraps. Cause: free-form,
  photo-heavy grids without clear table lines. Nothing is lost (codes/prices remain
  as searchable text), but those pages don't become clean SQL tables.
  *Fix path:* stronger table mode / OCR settings, and the Claude-oracle method
  (compare against the chatbot) — eval-graded, later.

## The brain

- **The brain can't RETURN photos yet.** The stores now hold every embedded
  photo (extracted, row-tagged, captioned, meaning-searchable — Session 20),
  and a direct store lookup answers "show me the image of item X" — but the
  planner has no photo lane, so a user asking the brain gets text only.
  *Fix path:* a photo-lookup step in the planner after the ingest gate ships,
  with its own known-answer eval ("show me the image of the best seller").

- **Plans are 2D only (no branching plans).** The planner writes the whole
  checklist upfront; a question whose NEXT step depends on an intermediate answer
  ("if growth is under 10%, investigate X; otherwise Y") can't be planned yet.
  *Fix path (parked, recorded):* the conditional / re-planner level — the plan
  revises itself between waves.

- **No conversation memory yet** — each question stands alone; "and compare it to
  last year?" is meaningless. *Fix path:* LangGraph checkpointing (brief #16).

## Retrieval

- **The same question can pick different sheets between runs.** A figure like
  "Blackpearl's April sales" can come from the Summary sheet (318) or the Sales
  sheet filtered by date (256 before the source dates were fixed) — the numbers
  form chooses, and it isn't deterministic. Session 26 surfaced it with a real
  62-gap. *Fix path:* make the sheet choice stable / prefer the summary for
  period totals, eval-graded — a named seam for a later session.

- **The final answer-writer sometimes splits one row into two bullets.** A single
  sale whose remark reads "Anchor Bracelet + Howlite Bracelet" can come back as two
  list items (Session 26, Blackpearl April). Routing and data are correct; this is
  a presentation wobble in the combine step. *Fix path:* tighten the list-rendering
  instruction, minor.

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
