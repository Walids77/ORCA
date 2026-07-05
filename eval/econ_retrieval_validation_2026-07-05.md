# Held-out Validation Eval — Economics module (does C=5 generalize?)

**Date:** 2026-07-05 (Session 6)
**Purpose:** the C=5 RRF setting scored 82.5% on the survey it was TUNED on — this
tests it on a DIFFERENT document it never saw, to check for overfitting.
**Document:** `data/econ_intro.pdf` — "Introduction to Economics" (110-page first-year
university module, Sept 2019). Covers micro (Ch 1–5) + macro (Ch 6).
**Store:** same ChromaDB, embedder = local all-MiniLM-L6-v2 (unchanged), **236 chunks**
(110 pages, 39 tables, 1 front-matter). **Config: hybrid + BM25, RRF C=5** — the winner,
applied AS-IS, no re-tuning.
**Questions:** a fresh 20 (9 micro · 7 macro incl. 1 compare · 2 metadata · 2 traps).
**Rubric:** same — did the right chunk land in the top-5?

## SCORE: 18/18 answerable ✅ + 2/2 traps clean  (effectively 20/20)

Every content question surfaced its exact section, most at rank 1:

| # | Question | Result |
|---|----------|:---:|
| E1 | Definition of economics | ✅ §1.1 rank 1 |
| E2 | Opportunity cost | ✅ rank 1 |
| E3 | Production Possibilities Frontier | ✅ rank 1 |
| E4 | Determinants of demand | ✅ §2.1.2 rank 1 |
| E5 | Price elasticity of demand | ✅ §2.1.3 rank 1 |
| E6 | Market equilibrium | ✅ §2.3 rank 1 |
| E7 | Assumptions of perfect competition | ✅ §5.2.1 in top-5 |
| E8 | Characteristics of monopoly | ✅ comparison table + §5.3.1 |
| E9 | Law of variable proportions | ✅ §4.1.4 rank 1 |
| E10 | Goals of macroeconomics | ✅ rank 1 |
| E11 | Approaches to measure GDP/GNP | ✅ §6.2.1 rank 1 |
| E12 | Nominal vs real GDP | ✅ §6.3 rank 1 |
| E13 | GDP deflator & CPI | ✅ §6.4 rank 1 |
| E14 | Business cycle | ✅ §6.5 top-2 |
| E15 | Inflation & causes | ✅ "Causes of inflation" rank 1 |
| E16 | Monetary vs fiscal policy | ✅ BOTH §6.7.1 + §6.7.2 in top-2 |
| M17 | Title of the document | ✅ front-matter rank 1 |
| M18 | Publication month/year | ✅ front-matter (contains "September 2019") top-2 |
| T19 | Cryptocurrency/Bitcoin (trap) | ✅ nothing false surfaced |
| T20 | ML models to forecast inflation (trap) | ✅ nothing false surfaced |

## C=5 vs C=60 on this document (objective section-hit@5, 18 answerable)
| Config | Score |
|---|---|
| C=60 (standard) | 18/18 |
| C=5 (tuned) | 18/18 |

**C=5 cost nothing here.** Both are perfect on this doc, so it doesn't discriminate the
two — but that is exactly the point: the tuned setting did **not break anything** on a
document it never saw.

## Verdict — the overfitting fear did NOT materialize
- On the SURVEY (hard doc, oblique headings): C=5 **helped** (+10 pts, rescued metadata).
- On the ECON module (new doc, literal headings): C=5 **matched** the standard, 18/18.
- **Together: C=5 helps on hard documents and doesn't hurt on easy ones → safe to adopt.**
- The metadata fix generalized: title AND publication date both retrieved here — the exact
  question type that failed completely on the survey before hybrid.

## Honest caveat
This econ module is an EASIER retrieval target than the survey: its section headings are
literal ("6.5 The Business Cycle", "1.1 Definition of economics"), so the question words
match the heading directly — both keyword AND meaning search do well. So 100% reflects a
friendly document as much as a strong config. The survey remains the harder stress test.
Real proof of generalization would keep accumulating docs (retail/finance next).

Re-run: `./.venv/Scripts/python.exe scripts/run_econ_eval.py`
