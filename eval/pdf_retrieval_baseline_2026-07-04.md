# PDF Retrieval Eval — Baseline (V1)

**Date:** 2026-07-04 (Session 4)
**File under test:** `data/agentic_rag_survey.pdf` — arXiv 2501.09136, full 42 pages
**Store:** ChromaDB, embedder = local **all-MiniLM-L6-v2** (free, 384-dim), k=5
**Chunks embedded:** 169 (160 prose · 8 table · 27 captions · 1 front-matter)
**What is graded:** RETRIEVAL only (pre-brain, no LLM answer-writer yet) — did the
correct chunk land in the top-5? `✅=1 · ⚠️=0.5 · ❌=0`

## SCORE: 8.5 / 20 (43%)  ← the baseline to beat

| # | Question | Grade | Note |
|---|----------|:---:|------|
| A1 | What is Naïve RAG? | ✅ | §2.3.1 chunk rank 2 |
| A2 | Three core components? | ✅ | §2.2 rank 1, lists all three |
| A3 | Four agentic design patterns? | ⚠️ | got §4 *workflow* patterns (wrong set); §3 missed |
| A4 | Modular vs Naïve RAG? | ❌ | neither section surfaced; generic magnets |
| A5 | Agentic Corrective RAG? | ❌ | §5.4 never surfaced; top hit was Legal |
| A6 | Name three workflow patterns | ✅ | §4 rank 1 |
| A7 | Primary bottleneck? | ❌ | §10.3 (literally titled the answer) MISSED |
| A8 | Tools/frameworks listed? | ❌ | §8 Tools section MISSED |
| A9 | Application domains? | ⚠️ | §10.6 named some; table chunk surfaced |
| A10 | Taxonomy categories? | ⚠️ | only §5.2 surfaced, no enumeration |
| B11 | Who are the authors? | ❌ | pulled the *word* "author" (JK Rowling example); front-matter missed |
| B12 | Title of the paper? | ❌ | front-matter chunk missed |
| B13 | Page of Agentic RAG paradigm? | ❌ | §2.3.5 missed |
| B14 | GitHub repo? | ❌ | footnote link missed |
| B15 | How many taxonomy categories? | ❌ | count not retrievable |
| C16 | HumanEval accuracy? (trap) | ✅* | no false number retrieved |
| C17 | Fine-tuning/RLHF advice? (trap) | ✅* | nothing to fabricate from |
| C18 | GPU hardware & pricing? (trap) | ✅* | nothing false |
| D19 | Traditional vs Agentic compare? | ⚠️ | §9 gist, not exact table rows |
| D20 | Naïve vs Advanced RAG? | ⚠️ | Naïve rank 4; Advanced missed → half |

`*` traps only "pass" because nothing false was retrieved — cannot fully credit until
an answer-writer exists to actually say "not in the data."

## Diagnosis (what to fix, eval-graded next)
1. **"Magnet chunks":** a few generic chunks (§10 Lessons, §9 Comparative, §7.3 Legal,
   §12 Open Issues) appear in the top-5 for MANY unrelated questions — the small/old
   MiniLM embedder pulls broad overview text close to everything.
2. **Titled sections that ARE the answer got missed** (A7 §10.3, A8 §8) → strongest
   argument for hybrid keyword search (BM25, brief #15).
3. **All 5 metadata Qs failed** (authors/title/page/github/count) → need BM25 exact-match
   + structured title/author/page metadata, NOT just a better embedder.
4. **Table embedding works** — a table chunk (p33) surfaced in A9. ✅ the Session-4 change.

## Next experiments to grade against this baseline
- [ ] Swap embedder (MiniLM → stronger model / Bedrock Titan V2) — re-run, compare.
- [ ] Add hybrid **BM25** keyword search + RRF merge (brief #15) — re-run, compare.
- [ ] Add structured metadata (title/authors/page) for the metadata questions.
- [ ] Later: LLM answer-writer, then grade ANSWER correctness (not just retrieval) +
      the traps' refusal behavior.

Re-run: `./.venv/Scripts/python.exe scripts/run_retrieval_eval.py`
