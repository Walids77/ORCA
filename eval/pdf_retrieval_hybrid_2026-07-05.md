# PDF Retrieval Eval — Hybrid (V2: vector + BM25 + RRF)

**Date:** 2026-07-05 (Session 6)
**File under test:** `data/agentic_rag_survey.pdf` — arXiv 2501.09136, full 42 pages
**Store:** ChromaDB, embedder = local **all-MiniLM-L6-v2** (UNCHANGED from baseline)
**New:** keyword search (`rank_bm25`, BM25Okapi) run alongside vector search, the two
ranked lists fused with **RRF** (C=60, pool=20). Code: `src/orca/stores/hybrid.py`.
**What is graded:** same as baseline — did the correct chunk land in the top-5?
Same 20 known-answer questions, same rubric (`✅=1 · ⚠️=0.5 · ❌=0`).

## SCORE: 14.5 / 20 (72.5%)  — up from 8.5 / 20 (43%) baseline

Same embedder, same chunks, same questions. The ONLY change is adding BM25 keyword
search + RRF merge. +6 points / +29 pts.

| # | Question | Base | Hybrid | What changed |
|---|----------|:---:|:---:|------|
| A1 | Naïve RAG? | ✅ | ✅ | §2.3.1 now rank 1 |
| A2 | Three core components? | ✅ | ✅ | §2.2 rank 1 |
| A3 | Four agentic design patterns? | ⚠️ | ✅* | §3 (Core Principles + §3.4) now surfaced |
| A4 | Modular vs Naïve? | ❌ | ✅ | **§2.3.3 Modular + §2.3.1 Naïve both surfaced** |
| A5 | Agentic Corrective RAG? | ❌ | ✅ | **§5.4 exact-title match → rank 1** |
| A6 | Three workflow patterns | ✅ | ✅ | §4 rank 1 |
| A7 | Primary bottleneck? | ❌ | ❌ | §10.3 still missed |
| A8 | Tools/frameworks listed? | ❌ | ✅ | **§8 "Tools and Frameworks" surfaced** |
| A9 | Application domains? | ⚠️ | ⚠️ | domains table (p33) surfaced, no §-enum |
| A10 | Taxonomy categories? | ⚠️ | ✅* | §5 Taxonomy chapter intro (p14) surfaced |
| B11 | Who are the authors? | ❌ | ❌ | front-matter p1 still missed |
| B12 | Title of the paper? | ❌ | ❌ | front-matter p1 still missed |
| B13 | Page of Agentic RAG paradigm? | ❌ | ✅ | **§2.5 "A Paradigm Shift" → rank 1** |
| B14 | GitHub repo? | ❌ | ❌ | footnote p1 still missed |
| B15 | How many taxonomy categories? | ❌ | ⚠️ | §5 taxonomy intro surfaced (count inferable) |
| C16 | HumanEval accuracy? (trap) | ✅* | ✅* | nothing false retrieved |
| C17 | Fine-tuning/RLHF? (trap) | ✅* | ✅* | nothing false |
| C18 | GPU hardware/pricing? (trap) | ✅* | ✅* | nothing false |
| D19 | Traditional vs Agentic compare? | ⚠️ | ⚠️ | §9 + §6 comparative surfaced, not exact rows |
| D20 | Naïve vs Advanced RAG? | ⚠️ | ✅ | **§2.3.1 Naïve + §2.3.2 Advanced both surfaced** |

`*` A3, A10 = borderline calls (the right *section* surfaced; worth a manual spot-check).
`*` traps still only "pass" as no-false-retrieval until an answer-writer exists.

## What BM25 fixed vs did NOT (the honest split)
- **FIXED — exact-term / section-title questions** (the whole point): A4, A5, A8, B13, D20
  all flipped ❌/⚠️ → ✅ because the question words literally match a section title
  ("Corrective RAG", "Tools and Frameworks", "Modular", "Advanced", "Paradigm Shift")
  that meaning-search glossed over. This is exactly the +15–30% lever brief #15 predicted.
- **NOT fixed — pure front-matter metadata** (B11 authors, B12 title, B14 github): still
  ❌. That info sits on page 1 and the query words ("authors", "title") don't appear
  *near* the answer, so neither vector NOR keyword search finds it. → confirms the
  baseline diagnosis: these need **structured title/author/page metadata fields**, NOT
  BM25 and NOT a better embedder. That's the next separate experiment.
- **Still missed — A7 bottleneck:** §10.3 didn't surface even by keyword; revisit when
  the embedder changes (Titan) or with reranking.

## Takeaway
Hybrid retrieval is a clear, eval-proven win (43% → 72.5%) with the embedder untouched —
so it stacks with the Titan embedder swap when Bedrock unblocks.

Re-run: `./.venv/Scripts/python.exe scripts/run_hybrid_eval.py`

---

# Follow-up experiment (same session) — tuning the RRF merge constant C

**Root cause found for the metadata misses:** the front-matter chunk (title+authors)
is BM25 **rank 1** for "authors" and **rank 3** for "title" — keyword search finds it
perfectly. But it sits at vector rank 43 / 94 (semantic search buries it), so it is in
only ONE of the two fused lists. With the standard `C=60`, RRF flattens rank gaps, so a
chunk present in only one list (even at rank 1) loses to mediocre chunks present in
BOTH. i.e. **the merge was diluting strong keyword-only hits.**

**Fix tested:** lower C so a top rank in one list counts for more. Objective page-hit@5
sweep (grader = does a top-5 chunk sit on the expected page; 16 answerable Qs):

| C | page-hit@5 | notes |
|---|---|---|
| vector-only | 7/16 | reference |
| 60 (default) | 13/16 | misses A7, authors, title |
| 20 | 13/16 | same |
| 10 | 13/16 | seesaws |
| **5** | **14/16** | **gains authors, title, A7; loses A10, B15** |
| 2 / 1 | 14/16 | no further gain |

**Hand-graded (same rubric as above) at C=5: 16.5 / 20 (82.5%).**
Gains vs C=60: B11 authors ❌→✅, B12 title ❌→✅, A7 bottleneck ❌→✅, D19 compare ⚠️→✅
(the p29 comparison table surfaced rank 1). Losses: A10 ✅→❌, B15 ⚠️→❌ (taxonomy p14).

## ⚠️ Honest caveat — this is tuned ON the test set
C was chosen by maximizing score on the SAME 20 questions we grade, on ONE document —
classic overfitting risk. And it's a **seesaw** (rescues metadata, drops taxonomy), not
a free win. So 82.5% is real for this paper but NOT proven to generalize.
- **Robust, ship-now win = hybrid itself (72.5% at the standard C=60).**
- **C=5 is a DIAGNOSTIC, not a verdict:** it proves the metadata failure is a
  merge/ranking problem, whose *principled* fix is a **reranker** (re-score a wide pool
  against the question — blocked today, needs a model) or a **metadata route** (detect
  "who/title/how-many" questions → answer from stored title/author fields).
- **Validate before adopting C=5 as default:** re-run the sweep on a SECOND document
  (e.g. a retail/finance file) — keep the low C only if it wins there too.

## Still-open failures (need separate work, not C-tuning)
- **B14 GitHub:** the paper's own repo link is NOT in the store at all — it lives in a
  page-1 **footnote**, and footnotes are dropped at extraction (`_PDF_NOISE_LABELS`).
  Fix = keep page-1 footnotes / links on re-ingest (verify the link exists first).
- **A10 / B15 taxonomy:** the §5 taxonomy-intro chunk is weak for "how many categories" —
  candidate for a reranker or a structured count field.

Sweep script: `scratchpad/rrf_sweep.py` (temp). Default C left at 60 pending validation.
