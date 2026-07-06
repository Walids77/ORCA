# PDF Retrieval Eval — V3: zero-score BM25 filter + page-1 footnote chunks

**Date:** 2026-07-06 (Session 8)
**File under test:** `data/agentic_rag_survey.pdf` — arXiv 2501.09136, full 42 pages
**Store:** ChromaDB, embedder = local **all-MiniLM-L6-v2** (still unchanged)
**Setup:** hybrid (BM25 + vector, RRF **C=5**, pool=20) — same as the 82.5% run, plus
two changes this session:
1. **Zero-score BM25 filter** (`hybrid.py`): chunks sharing NO word with the query no
   longer enter the fusion (they used to collect RRF points just for occupying a rank).
2. **Page-1 footnotes kept as standalone chunks** (`records.py`): footnotes were dropped
   wholesale at chunking; now page-1 footnotes (where an arXiv paper's GitHub link and
   contact info live) each become their OWN small chunk. First attempt folded the
   footnote into the big ABSTRACT chunk — eval showed it still failed (drowned by
   BM25 length normalization; the References chunks full of github.com URLs out-ranked
   it). Standalone-small is what fixed it. Footnotes on later pages stay dropped
   (citation noise).

**What is graded:** same rubric as all previous runs — did the correct chunk land in
the top-5? (`✅=1 · ⚠️=0.5 · ❌=0`, 20 known-answer questions.)

## SCORE: 17.5 / 20 (87.5%) — up from 16.5 / 20 (82.5%)

| # | Question | C=5 (S6) | Now | What changed |
|---|----------|:---:|:---:|------|
| A1 | Naïve RAG? | ✅ | ✅ | §2.3.1 rank 1 |
| A2 | Three core components? | ✅ | ✅ | §2.2 rank 1 |
| A3 | Four agentic design patterns? | ✅* | ✅* | §3 + §3.4 surfaced (borderline, unchanged) |
| A4 | Modular vs Naïve? | ✅ | ✅ | §2.3.3 + §2.3.1 both in top-5 |
| A5 | Agentic Corrective RAG? | ✅ | ✅ | §5.4 rank 1 |
| A6 | Three workflow patterns | ✅ | ✅ | §4 rank 1 |
| A7 | Primary bottleneck? | ✅ | ✅ | §10.3 rank 4 |
| A8 | Tools/frameworks listed? | ✅ | ✅ | §8 rank 3 |
| A9 | Application domains? | ⚠️ | ⚠️ | domains table (p33) rank 1, no §-enumeration |
| A10 | Taxonomy categories? | ❌ | ❌ | §5 intro still missed (known C=5 seesaw loss) |
| B11 | Who are the authors? | ✅ | ✅ | front-matter rank 4 |
| B12 | Title of the paper? | ✅ | ✅ | front-matter rank 5 |
| B13 | Page of Agentic RAG paradigm? | ✅ | ✅ | §2.5 rank 1 |
| B14 | GitHub repo? | ❌ | ✅ | **"Footnote (page 1)" chunk → HYBRID RANK 1** |
| B15 | How many taxonomy categories? | ❌ | ❌ | still needs reranker / structured count |
| C16 | HumanEval accuracy? (trap) | ✅* | ✅* | nothing false retrieved |
| C17 | Fine-tuning/RLHF? (trap) | ✅* | ✅* | nothing false |
| C18 | GPU hardware/pricing? (trap) | ✅* | ✅* | nothing false |
| D19 | Traditional vs Agentic compare? | ✅ | ✅ | p29 comparison table rank 1 |
| D20 | Naïve vs Advanced RAG? | ✅ | ✅ | §2.3.1 + §2.3.2 both in top-5 |

`*` same borderline/trap conventions as previous runs.

## Notes
- **No regressions.** Every question kept its Session-6 grade; the GitHub question
  flipped ❌→✅. The zero-score filter alone (measured before the footnote fix landed)
  also held 82.5% exactly — it removes a noise risk without costing anything.
- **The footnote chunk now pokes into a few other top-5s** (rank 5 for the authors and
  page-of-paradigm questions) without displacing correct chunks. Watch it on future
  docs — a small chunk is BM25-attractive; if it starts displacing right answers,
  cap footnote chunks' RRF weight or route them by metadata.
- **Teaching point this run proved:** an ingest fix isn't "done" when the data is in
  the store — the FIRST attempt stored the link but retrieval still failed (wrong
  chunk shape). Only the re-run scorecard caught it. Eval-before-believing.
- **Still open (both need a model → Bedrock):** the two taxonomy questions (reranker
  or structured count field), Titan embedder eval on top of this 87.5%.

Re-run: `./.venv/Scripts/python.exe scripts/run_hybrid_eval.py`
