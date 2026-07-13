# ORCA — Development Log

> Newest entry first. One dated entry per work session.

## 2026-07-14 — Session 19: the surveyor hardened by three eval rounds — Layer 1 closed
> Parser internals stay private (see `private/`); this entry records method + measured results.
- **Scouted the research for the Excel shapes that exist in the wild** (the DECO/Enron corpus:
  75% of real sheets hold more than one region; Microsoft's SpreadsheetLLM) → generated **7 dummy
  workbooks**, one per shape (multi-table, cross-tab, pivot-style, dates-as-headers, invoice,
  indented hierarchy, all-text), each with the expected result **written down before the run**.
  Score: 4 pass · 1 partial · 3 fail — predictions **8/8 correct**, and all three fails shared ONE
  root cause: **totals stored as plain numbers, with no formula to betray them** (exactly how
  PivotTables and hand-typed subtotal rows store them).
- **Mutation round (Walid's idea = real mutation testing):** typed values into known zones of a
  COPY of a real workbook — the blank "sea" between tables, the template zone, the total row, a
  header cell. 4 exact passes (appending a sale line grows the table by exactly one row); two
  typed cells in the gap **glued two tables into one** (proving blank space is the only wall —
  now Layer 2's job to catch by meaning, Walid's call); and one test was voided by a discovery
  bigger than the test: **files saved by software (not Excel) drop every formula's cached result**,
  leaving any structure reader half-blind. That became a new gate warning.
- **Built 12 levers, each re-eval'd against a before/after net over all 10 test files** (3 real
  workbooks + 7 dummies): plain-value aggregate rows caught by re-doing the math ourselves —
  **SUM / AVERAGE / COUNT / MIN / MAX**, each firing only when the row's label claims it (a decoy
  client named "Max Weber" was correctly NOT flagged); total rows removed from real-record counts
  (the May sheet now reads **22 real rows — the human count**; the old 23 double-counted the TOTAL
  row); the "saved by a tool, not Excel" warning; dates/years accepted as column names (a
  time-series sheet's 6 unnamed columns fixed); sentence-length header names flagged; header
  search deepened to 15 rows; font-size title detection. The net also **caught one real regression
  mid-round** (a summary sheet briefly misfiled as a data table) — fixed and re-proven same day.
- Bonus catch on the real workbook: naming number-typed header cells exposed a **duplicate column
  header** no one had noticed. Three eval records added under `eval/`.
- **Layer 1 declared CLOSED** (no more levers without a failing eval demanding them). Next
  session: hidden rows/columns detection + a dummy finance sheet (P&L — the hardest proven shape)
  as Layer 1's final exam, then **Layer 2**: the LLM names each region's meaning.

## 2026-07-13 — Session 18: structure-aware Excel ingestion + the fix-or-proceed gate
> Note: the parser's internals are kept private (see `private/`, not in this repo). This entry
> records the problem, the design decisions and the measured results — not the method.
- **Started as the ingest notification-gate design; became the pillar underneath it.** Industry
  check: mature data pipelines **quarantine bad rows, they don't reject files** — but RAG
  pipelines **do** stop before indexing and ask a human when confidence is low. Design agreed:
  **BLOCK** only if nothing is readable (password-protected, empty) · **FIX-OR-PROCEED** for
  anything that would make ORCA confidently **WRONG** (an unlabelled total, a misread header,
  broken dates) · **WARN + PROCEED** for anything that only makes answers *worse* (spelling
  variants, sparse cells). **Never reject a file; never ingest silently.** Guiding principle:
  *a company will not reshape a thousand spreadsheets to suit our RAG — the parser bends, not them.*
- **Tested the existing reader on two REAL business workbooks; it failed SILENTLY** — the worst
  failure mode, because nothing looks broken. On a 30-sheet corporate workbook it mistook a
  decorative banner for the header row (most columns ended up unnamed), reported **878 data rows
  where 22 exist**, and merged three side-by-side tables into one — while raising a single warning
  for the entire file. Separately, a fresh copy of a workbook cleaned in Session 16 came back with
  its data errors **restored** → **data quality DRIFTS**: the gate must run on *every* upload,
  not just the first.
- **Built a structure-aware sheet reader** (read-only, no LLM, nothing stored). It reports what it
  understood *before* anything is ingested: where the real tables are, the true header row (with a
  confidence score), multi-level headers, which rows are real records vs totals vs unused template
  rows, what each column is *for* (exact-filterable category vs free text vs computed), which
  columns are sparse **by design** (an empty cell there means zero, not missing), and which tables
  **feed** which — within a sheet and across sheets. On the hard workbook it now reads the correct
  header row, keeps **23 real rows instead of 878**, separates the side-by-side tables, and catches
  a TOTAL row that sits *above* its data. The clean workbook still reads correctly — no regression.
- **Why a human gate at all — the evidence:** the best *published* spreadsheet table detection
  scores **78.9% F1** (SpreadsheetLLM, Microsoft Research) — roughly **one table in five gets its
  boundaries wrong**. Full automation is not achievable today, by anyone. That is the argument for
  showing the user what we understood and letting them confirm. Benchmarked the standard library
  (`unstructured`) head-to-head on the same sheet: it returned **879 rows, 47,081 empty cells and
  304 KB of HTML** for a sheet holding 22 sales, with side-by-side tables merged and no awareness
  of headers or totals. **No off-the-shelf tool solves this.**
- **Settled: `.xlsx` stores no per-cell edit history** (Track Changes must be enabled beforehand;
  Show Changes needs OneDrive/SharePoint). So ORCA will **build that history itself** by diffing
  each re-upload against the last — cells that never change are structure, cells that grow downward
  are the living data. A live source connector (item #18) would provide the real history for free.
- **Next:** render each detected table in a clean form for the vector store → then let the LLM name
  what each table **means** (auto-filling the sheet-meanings catalog) → then ship the user-facing
  fix-or-proceed report. This one build closes item **#11**, the **notification gate**, and
  **organ #5** of the CPU backlog (clarify-with-the-user).

## 2026-07-12 — Session 18 (opening): round vs wave + the roadmap gets a visual (discussion, no engine code)
- **Walid restated the round/wave timing model in his own words — confirmed correct,**
  two nuances added: (a) it's one small form PER STEP, not one form for the whole round
  (several get written together only because several steps are ready together); (b) a
  later round's form can't be written earlier because its question has a blank that
  only the previous round's result fills.
- **Naming preference locked (conversation-only):** say "round 1, round 2…" to Walid,
  never "wave" — he can't visualize "wave", "round" is concrete. Explicit call: do NOT
  rename anything in code (`runner.py`, `planner.py`, `graph.py`, `state.py`) or in
  existing docs/session history — those keep "wave".
- **Built a Now/Next/Later roadmap** (Claude Artifact) answering "what's still waiting
  after Session 18?" — then registered the missing piece into `progress.html`: the
  **CPU growth backlog now has its own numbered visual block** (was prose-only before),
  same style as the Excel 7-stage pipeline.
- **Session 18's 3 locked items are still queued, unchanged:** design the ingest
  notification gate (discuss first) · stabilize the numbers form (few-shot dictionary ·
  lower temperature · retry-on-empty, re-eval'd no-lucky-passes) · owed housekeeping
  (spelling cleanup · pytest + CI · AWS case check).

## 2026-07-11 — Session 17: brain-flow rehearsal + the CPU growth backlog (discussion, no engine code)
- **CPU gap review (Walid's opening question).** Confirmed the three lanes (text · numbers ·
  calculate) + the 2D planner cover single questions; the five missing organs are now a
  saved, prioritized **CPU GROWTH BACKLOG** in the brief — conversation memory · a capped
  judge-and-retry loop · an answer self-check · the conditional re-planner (3D) · a
  clarify-with-the-user path — each to be built one at a time and eval-gated ("earns its keep").
- **Rehearsal done — Walid owns the CPU.** Walked the real February trace station by station,
  each with a judging question. He correctly explained the placeholder/dependency, localized
  the SUM-instead-of-COUNT fault to the FORM (not the SQL) from the answer's shape alone, and
  proposed the fix himself (a dictionary of question examples = few-shot examples — already
  lever 1 of the form-stabilization task).
- **Timing model locked:** the plan is written ONCE upfront; each step's form is written
  JUST-IN-TIME when its wave runs (step 2's form can't exist before wave 1 — its question is
  incomplete until the handoff fills the placeholder); the runner loops one lap per wave.
- **New diagnostic rule taught:** *fails sometimes = an AI move; fails always = our code* —
  flakiness is a fingerprint that tells you which kind of station to open.
- **Saved for re-reading:** `brain_flow_timeline.md` (git-ignored — real figures): the full
  timeline diagram + timing table + Walid's 6-rule trace-reading card.
- **Next session (18):** design the ingest notification gate (fix-or-proceed before parsing) ·
  stabilize the numbers form (few-shot dictionary + lower temperature + retry-on-empty,
  re-eval'd on the 15-question set) · owed: spelling cleanup, pytest + CI, AWS case check.

## 2026-07-11 — Session 16: CALCULATE worker + catalog meanings + clean-data round — first 15/15
- **Planner = the default brain.** `build_brain()` now builds the planner+waves CPU
  (was "parallel" — demos/evals could accidentally run the old design; the session's
  code-review file flagged it first). Older designs stay selectable; the historical
  20-question survey eval pinned to its original wiring.
- **Caged CALCULATE worker (the third lane).** The planner picks a whitelisted math
  function (divide/ratio · difference · percent-change · projection) and names which
  step answers feed it; OUR tested code extracts the numbers and computes — zero LLM
  calls in the lane, cage rejections unit-tested. The Session-13/15 average-basket
  question now passes every run.
- **Catalog MEANINGS.** One plain-English line per sheet (`data/sheet_meanings.json`,
  git-ignored) injected into every catalog the planner/router/form sees — ambiguous
  words now map to the right sheet ("what was bought" → client Sales, not company
  Expenses; the Session-15 December fail is closed). Tuning = editing text, not code.
- **Per-step safety net:** a crashing step fails alone with a stored reason; the
  combine answers the parts that worked.
- **Purge-first re-ingest (bug found by real use):** Walid's renamed "% Profit"
  column crashed re-ingest (the old table layout lingered) → the Excel path now
  drops all of a file's tables first, like the PDF path. Standing policy (Walid):
  re-upload = delete ALL the file's traces from BOTH stores, then store fresh.
- **Refined-data round:** Walid applied the workbook fix list (`data/OB7OLA_FIX_LIST.md`)
  — invoices total, Client + Items columns, month cells, header rename, date cells,
  stale total cells. Quality scan: 14 → **0 issues**. The ingest proof-check caught the
  stale Invoices/Orders/Expenses/Profit totals BEFORE he fixed them (the checker works).
- **Eval (4 runs, no-lucky-passes):** 13/15 · 14/15 (mid-fix) · 11/15 · **15/15 — the
  first perfect run ever**. Stable 4/4: 11 questions incl. February DEPTH + CALCULATE.
  Flaky: the fragile survey fact (retrieval-precision pile) + numbers-form
  nondeterminism (once SUM-instead-of-COUNT; list steps occasionally empty). Plan layer
  60/60 correct. Average-basket key re-verified to **22.99** (the source is now
  self-consistent). Record: `eval/refined_data_2026-07-11.md` (git-ignored).
- **`brain_flow_2d.html`** (git-ignored): interactive click-through of the REAL
  February 2D trace — planner → wave 1 → handoff → wave 2 → combine, with the
  notebook filling live. Built for next session's rehearsal.
- **Next session (17):** rehearse the brain flow with Walid; design the ingest
  NOTIFICATION GATE (show data problems to the user to fix-or-proceed BEFORE full
  parsing — item #11 grown up); stabilize the numbers form; spelling cleanup (#6) owed.

## 2026-07-10 — Session 15: the router becomes a PLANNER + plan-runner in parallel waves — SHIPS at 12/13
- **Morning research (Walid's brainstorm):** RBAC-in-the-router, catalog scaling, branch-
  selection best practice, the "3rd dimension", music embeddings — web + GitHub checked.
  Headline finding: Walid's checklist-with-waves design IS the published **LLMCompiler**
  pattern (ICML 2024) — independently derived.
- **RBAC fence (shape 1):** the catalog builders now take an allowed-files input — OUR
  script filters what the planner may even see, per user, before any prompt exists; the
  LLM never picks its own catalog. Fence 2 (filtering inside the search legs) lands with
  the multi-user layer.
- **PLANNER:** the router now writes a checklist into the notebook — focused question ·
  lane · waits-for (`{step N}` placeholders carry dependencies). Caged by our code:
  1–8 steps, real lanes, dependencies only point backward, unreadable → both-lanes fallback.
- **PLAN-RUNNER:** one station with a capped loop-back edge; each lap runs every ready
  step IN PARALLEL through the same proven legs (waves); placeholders filled between waves.
- **Eval (13-question regression set + 2 new depth cases; keys re-verified vs the source):
  FINAL 12/13 — beats the router's 11/13. The February depth question (highest month →
  what clients bought THAT month) passed IN FULL for the first time ever.** Plan shape
  15/15 in every run; both traps refused; flat questions ~$0.002–0.005, depth ~$0.01–0.02.
- **Five diagnosis loops, all recorded:** plain-business-language steps (the planner
  decides WHAT, never HOW) · dates rendered both ways ("February 2026 (2026-02)") ·
  period-filtered steps must take the numbers lane (the text corpus contains no month
  words, only ISO dates) · "WHAT was bought" = LIST incl. remarks (cap 20→40) ·
  dependency labels only, never figures (an injected figure became a bogus SQL filter).
  Meta-lesson: multi-agent failures are mostly HANDOFF failures between steps.
- **Known fails with named levers (Session 16):** arithmetic (the perfect 3-step divide
  plan exists — the caged CALCULATE worker doesn't yet) · catalog MEANINGS (one-line
  description per sheet, so "what was bought" maps to client Sales, not company Expenses).
- **New public doc:** `docs/EXCEL_DATA_BEST_PRACTICES.md` — 12 data-entry/layout rules,
  each traced to a real eval-caught failure.
- **Standing rule (Walid): no lucky passes** — a pass that doesn't reproduce counts for
  nothing; evals must verify stability. The 2D planner+waves engine = ORCA's CPU: harden
  it with many eval rounds (current data → refined data → new datasets, incl. finance).
- Parked, recorded: simulation level (user assumptions on the calculate worker) ·
  conditional/re-planner ("3rd dimension") · scaling bucket (catalog-search, ~100 users).

## 2026-07-10 — Session 14: parallel legs + router + token meter — three designs eval'd head-to-head
- **Token/cost meter built (roadmap item #20)** into the one-file LLM adapter: every call
  records purpose · tokens in/out **from the provider's own usage report** · cost at the
  paid-tier price table (free tier today, so actual spend $0; the Bedrock swap only changes
  the table). Acceptance check passed: meter split sums exactly to the provider's total.
  Learned: hidden **thinking tokens** are billed as output — a 1-character answer billed 43
  output tokens.
- **Parallel legs (first real branch):** text + numbers legs now fan out from START together
  and fan in at combine. Smoke test caught a real concurrency bug — SQLite refuses
  cross-thread connections → the SQL store now opens one connection per thread.
- **Router built:** reads the spreadsheet catalog + the text-document list, picks the lane
  (text / numbers / both), and **splits compound questions** into a focused sub-question per
  leg. Unreadable reply → safe fallback to "both". All three wirings stay selectable.
- **Three-design eval** — one fixed 13-question mixed set (5 text · 5 numbers · 3 both-legs,
  2 traps; keys verified against the SOURCE, never the store; record local-only, real names):
  **straight 9/13 (both-legs 0/3, 8.6 s) → parallel 11/13 (6.2 s, −28%) → router 11/13,
  lane picks 13/13, 5.7 s.** First-ever graded BOTH-legs pass = the supplier question (exact
  total [numbers] + the two supplier-credit remarks cited) — ORCA's differentiator working.
- **Honesty findings:** run 2's both-legs jump was an LLM coin-flip (the one-shot form
  sometimes engages on compound questions), NOT the parallel wiring — the router's
  deterministic split is the real fix and the reason it ships; its cost saving is ~neutral
  at this corpus size (the router pays its own toll). The February depth question (highest
  month → what was bought THAT month) failed all 3 runs **by design**: a dependency, not a
  lane choice.
- **Session-15 plan locked with Walid:** router→**planner** (writes a checklist: focused
  question · lane · waits-for) + a capped **plan-runner** that executes the checklist in
  parallel **waves** over the same proven legs. Three eval cases ready: February ·
  "best month 2026 vs 2025 + items of each" · the average-basket ratio (calculate step).
- Commits: `b9cf641` (code) + this session's docs commit.
- **The numbers leg now ANSWERS** (was: only listed tables). Two caged moves in the new
  `brain/numbers.py`: MOVE 1 — the LLM sees the data **catalog** (sheets · columns + types ·
  one sample row) and fills a structured **form** (sheet / SUM·AVG·MIN·MAX·COUNT·LIST /
  column / filters / group-by); MOVE 2 — **our validated code** builds + runs the SQL
  (identifiers checked against the catalog, values parameterised, Total rows always excluded).
  The LLM never writes SQL. Combine gets the result as an "EXACT NUMBERS — use verbatim,
  cite [numbers]" block.
- **Known-answer eval on the real retail Excel** (10 figure-questions, 4 Walid's + 6 Claude's
  incl. a trap; `scripts/run_numbers_eval.py`, record in `eval/numbers_eval_2026-07-09.md`,
  kept local — real business data): run 1 = 9/10 on paper but **honestly 7/10** — Walid
  challenged two figures and both were WRONG from one root bug.
- **Root bug: UNLABELLED total rows** (a grand-total row with no "Total" text) passed the
  keyword detector and doubled sums (average/pending questions). **Fix = 3 detectors,
  union:** label (existing) · **formula** (Walid's idea — a 2nd formula-mode pass over the
  file: a vertical `=SUM(...)` down the sheet's OWN column = a total row; row-wise sums and
  ranges pointing at OTHER sheets must not trip it — the Summary's monthly rows are built
  from `=SUM(Sales!…)` and are data) · **shape** (mostly-empty row whose number equals the
  column's sum). After the fix every column with a printed total matches to the cent.
- **2nd fix:** a no-rows query used to surface as `value = None` and the answer-writer once
  echoed "sales were None" — the evidence block now says **"NO DATA — matched no rows"** in
  words → the refusal is deterministic. Final eval: **10/10** (trap included).
- **METHOD LESSON:** run 1's answer key was computed from the ingested store → it inherited
  the store's bug and graded two wrong answers PASS. Keys must be verified against the
  SOURCE, and out-of-range figures chased (Walid's eyeball check caught what the green
  scoreboard missed).
- **Stage 6 data-quality scan** (seed of roadmap #11): ingestion now REPORTS source-file
  problems with exact rows — found 14 real ones (year-1900 dates, text like "23 april" in a
  date column). Face-value rule locked: store what the cell shows; read formulas only to
  UNDERSTAND values; never auto-correct data — the user fixes the source.
- **Scope growth proven on live questions:** LIST operation (capped, validated) for
  "show me…" questions; text leg now searches the WHOLE tenant corpus by default (client
  names live in free-text remarks; the survey eval stays pinned to its document). Verified:
  a client-purchases question answered complete-and-correct from remark chunks; a
  wish-list filter question exact; "top clients by sales" correctly REFUSED (no client
  column exists — agreed: fixing the sheet is the user's job, ORCA never invents columns).
- **Visual:** `brain_trips.html` — three real trips (numbers-carried · text-carried · trap
  refused) drawn station by station with the actual form/SQL/chunks (kept local — contains
  real business data).
- **Next session (rehearse together first, then build, then eval):** (1) make the two legs
  run in PARALLEL (fan-out/fan-in — the first real branch); (2) eval the never-tested
  BOTH-legs question type (exact number + text explanation in one answer = ORCA's
  differentiator); (3) let that eval's evidence justify the router. Ratio math (average
  basket = sales ÷ invoices) logged as the calculate-worker's first eval case.

## 2026-07-09 — Session 12: brain SKELETON built + first answer-level eval
- **Built the straight-line brain** `src/orca/brain/` (the middle spine, no branches/loops yet):
  `question → text leg → numbers leg → combine → answer`. The notebook (shared state), the three
  stations, and the map are separate small files (`state.py` · `nodes.py` · `graph.py`).
- **Wired to the REAL engines** (not fakes): text leg = `HybridSearcher` (meaning + keyword),
  numbers leg = `SqlStore`. Proven end-to-end in the terminal on real embedded data
  (`scripts/run_brain.py`).
- **Two-step build (simplest first):** (1) proved the road with a plain non-AI "combine" that
  just lists what each leg found — deterministic, free; (2) swapped in the real **Gemini** thinking
  node behind a **one-file adapter** (`llm.py` — the only place that names the model; Bedrock/Claude
  swap later = this one file). Installed `google-genai`; key stays in the git-ignored `.env`.
- **Anti-hallucination from day one:** the combine node answers ONLY from the retrieved passages,
  cites them, and refuses ("I can't answer that from the uploaded documents.") when the evidence
  isn't there.
- **First ANSWER-level eval** (`scripts/run_brain_eval.py`, results in
  `eval/brain_answer_baseline_2026-07-09.md`): all 20 known-answer Qs run through the brain →
  **≈13–15/20 (~65–75%)** first-pass. All 3 not-in-doc traps correctly refused; authors/title/GitHub
  (all failed at the old 43% baseline) now pass. Failures sorted into two piles: **refused-but-
  answerable** (chunk missed → raise k / reranker / loop) and **confidently-wrong** (trusted a
  plausible wrong chunk → retrieval precision + an answer self-check).
- **Next session:** review the 20 answers WITH Walid, confirm the grades, then test the cheapest
  Pile-1 fix first (raise k, one pass), re-run this exact eval, and only earn a reranker/loop if the
  eval proves one pass can't do it.

## 2026-07-08 — Session 11: brain map drawn + the "autonomous analyst" upgrade (design, no code)
- **Drew ORCA's full brain map** — saved as **`langGraph.html`** (companion to Session 9's
  `langgraph_visual.html`): guard → load memory → **router** (reads a catalog of the tenant's
  data + its agreed definitions) → three paths (answer directly / one lookup / **decompose**) →
  shared retrieval core → **combine** → self-check → answer; human can challenge, conversation
  continues on the cached memory.
- **The core shift Walid drove:** ORCA must answer **analysis questions**, not just retrieval.
  "What's the leave policy?" = a lookup; **"which department is overstaffed?"** = a conclusion
  that exists in no document — it must be **computed and judged** ("the autonomous analyst").
- **Three design upgrades to the map:** (1) the router's **data catalog** also holds the tenant's
  agreed **benchmarks** (what "overstaffed" means for this company); (2) the decompose branch gains
  a 2nd worker type — **CALCULATE** — that is **caged**: it calls pre-built, tested functions
  (ratio/variance/trend), never AI-written code/SQL (keeps the security rule + makes each number
  eval-checkable); which functions to build is revealed by the 100+ test questions, then hard-coded.
  (3) COMBINE returns a **3-layer labelled answer** — the exact numbers · a grounded diagnosis (AI
  connecting those numbers, still traceable) · a fenced "general insight" (AI's own experience,
  labelled "suggestion, not from your data", never overrides the numbers). Decision support, not
  decision-making.
- **Mapped the 4 BI question levels** (descriptive/diagnostic = built · predictive/prescriptive =
  future branches) → answered "can we add branches later?": a new question *shape* is free (router
  re-plans over the same roads); only a new *capability* (forecast, web search) needs a new station.
- **Bigger realization:** ORCA is a repeatable, tailorable per-company service — sample files →
  100+ questions → eval → fix → tailor — which IS the AI Solutions/Implementation Engineer job.
- No engine code changed. **Next (Session 12): build the brain skeleton** `src/orca/brain/` = the
  middle spine (question → three retrieval legs → combine) on Walid's go, prove it in the terminal,
  then earn each upgrade by eval. Keep checking AWS case `178327435100356`.

## 2026-07-08 — Session 10: LangGraph concepts locked (discussion-only, no code)
- Concept-only session at Walid's request — understand LangGraph before building. He now owns the
  **map model** (nodes = stations · edges = roads · conditional edges = junctions · the notebook =
  shared state) and the **5 standard branch patterns** (reinvented 3 himself; learned
  orchestrator–workers = ORCA's decompose branch, and the capped evaluator loop).
- Settled the key design question: **fixed map, dynamic plan** — the LLM writes a plan the fixed
  graph executes; it never redraws roads at runtime (un-evaluable). Router rules brainstormed:
  domain-first via a **data catalog** → structured plan (breadth × depth) → each rule an eval column.
- Smoke test recreated **as a saved file** (`scripts/langgraph_smoke.py`, green). Standing rule set:
  Walid works on logic only, never reads code.

## 2026-07-07 — Session 9: brain phase opened — LangGraph installed + Gemini as temporary LLM
- **AWS support case still pending** (Bedrock enable can take ~a week) → per the plan,
  moved to **0a step 3: the LangGraph agent brain** instead of waiting.
- **LangGraph 1.2.8 installed** into the project virtualenv (added to `requirements.txt`).
  **Smoke test passed:** a minimal 2-node graph (greet → shout) ran end-to-end, proving
  nodes execute in order and pass data through the shared state ("the notebook").
- **Temporary brain LLM locked = Gemini `gemini-2.5-flash`** until Bedrock unblocks.
  Design agreed: the LLM sits behind a one-file **adapter** — every brain node talks to
  the adapter, never to Gemini directly, so the later swap to Claude/Bedrock is a
  one-file change + an eval re-run. Key stored in `.env` (git-ignored, verified);
  live-tested: model list OK, `gemini-2.5-flash` answered the test prompt exactly
  (`gemini-3.5-flash` gave a 503 server-overload — Google's side, retry anytime).
- **`langgraph_visual.html` created** — a visual one-pager for Walid: what LangGraph is
  (a flowchart that runs: nodes/edges/notebook), the smoke test drawn, the three arrow
  tricks (decision fork · parallel branches · capped loop-back), and ORCA's target brain
  graph color-coded (green = the 3 built retrieval legs · orange = the LLM nodes).
- No engine code changed. **Brain skeleton ON HOLD** — Walid wants to understand
  LangGraph first; next session opens with a LangGraph discussion, then the skeleton
  (`src/orca/brain/`: the real notebook/state + the three legs as nodes).

## 2026-07-06 — Session 8: retrieval 87.5% (zero-score + footnote fixes) + PDF table→SQL
- **Fable-5 code review of the retrieval logic vs 2026 best practice** (web-checked):
  the hybrid BM25+vector+RRF design IS the industry-standard baseline; C=5 tuning
  matches published guidance (low C = trust a #1 rank in one list). Next levers
  confirmed = reranker (highest ROI, needs a model) + real embedder. One real flaw
  found: BM25 returned its top-20 even when scores were 0.
- **Zero-score fix** (`stores/hybrid.py`): chunks sharing NO word with the query no
  longer enter the RRF fusion (they used to collect points just for occupying a rank —
  risky with C=5). Verified: nonsense query → 0 keyword hits; score held at 82.5%.
- **Footnote fix = Option A** (`ingest/records.py`): page-1 footnotes are no longer
  dropped. **First attempt failed the eval** (link folded into the big ABSTRACT chunk →
  drowned by BM25 length normalization) — the re-run scorecard caught it. Fix that
  worked: each page-1 footnote becomes its OWN small chunk. **GitHub-link question now
  hybrid rank 1.** Retrieval **82.5% → 87.5%** (17.5/20), no regressions.
  Details: `eval/pdf_retrieval_footnote_2026-07-06.md`.
- **PDF table→SQL = Option B** (`ingest/pdf_tables.py`, new stage): stitch page-grids
  back into one table (re-printed / missing / data-mistaken-for-header cases — the last
  RESCUES rows Docling was losing) → type cells ("$1,234.56"→1234.56, "(500)"→-500,
  "12%"→12.0, dates) → flag summary rows by keyword AND by shape (label+value ladder:
  "Initial", "Final to pay"…) → classify number-table (→SQL) vs word-table (vector-only).
  Output = the Excel `SheetTable` shape, so `SqlStore` stores PDFs UNCHANGED. Added
  `store_pdf_tables` + `purge_file` (stale tables on re-ingest with changed layout).
- **Proven on the real purchase-order PDF:** 7 page-grids → ONE 36-row table (31 items +
  5 flagged summary rows); row-math 29/29 Cost×Quantity=Total Cost; **SUM(items) =
  1191.86 = the document's own printed "Initial" total, to the cent.** Survey PDF's 5
  comparison tables all correctly classified word-table → vector-only.
- **Limitations logged** (data-quality-advisor material, brief item 11): one row's cost
  buried in its description text; one merged cell ("$9.55 4.00") — source messiness, not
  chased.
- **Next (Session 9):** check AWS support case `178327435100356` → if unblocked, Titan
  embedder eval on top of 87.5%; if still blocked, start the **LangGraph agent brain**
  (skeleton + retrieval nodes are model-free; LLM decision nodes need Bedrock — or
  decide on a temporary key). All three legs the brain orchestrates now exist:
  meaning search · keyword search · exact-number SQL.

## 2026-07-06 — Session 7: reassessed the "metadata route" + communication rules (no code)
- **Verification-first review.** Before building the planned "metadata route", re-read the
  code + the Session-6 eval. **Finding: it's largely redundant** — the C=5 hybrid merge from
  Session 6 already fixed the metadata questions ("who are the authors?", "what is the title?"
  both now correct; they only failed at the old 43% vector-only baseline).
- **What actually remains, still model-free (no Bedrock):** (1) the GitHub-link question — the
  link is in a page-1 **footnote**, which is dropped at extraction (`records.py`,
  `_PDF_NOISE_LABELS`), so it never enters the store; (2) "how many taxonomy categories" — weak,
  wants a reranker (needs a model) or a count field.
- **LOCKED for next session — pick one (both model-free):** Option A = keep page-1 footnotes so
  the GitHub link is found, then re-run the eval; Option B = the PDF **table→SQL** step (number-
  tables into the exact-numbers DB). Claude leans B (retrieval is good enough at 82.5%).
- **Communication rules added to `CLAUDE.md`** (Walid's ask): keep the real term but always add a
  one-line plain-English meaning; and **never use letter/number codes** ("B14", "A7") — spell out
  the whole question/word every time.
- No engine code changed. Details: `memory/metadata_route_reassessed.md`.

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
