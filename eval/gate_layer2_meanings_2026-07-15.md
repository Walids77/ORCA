# Eval — Gate Layer 2: the LLM names each region's MEANING + the glued-table check

**Date:** 2026-07-15 (Session 21)
**What is graded:** Layer 2 of the ingest gate. Layer 1 (code) maps a sheet's
structure; Layer 2 hands that MAP (plus a few sample rows and pre-computed
suspect flags — never the whole sheet) to the LLM, which returns a strict JSON
form: one meaning line per sheet, one per region, and a verdict per region —
is this block ONE table, or TWO+ different tables glued together with no blank
space between them? (Code cannot see that wall — proven by the Session-19
mutation test; the blank sea is its only separator.)

The LLM only REPORTS a suspected glue point. It never splits anything — the
gate (Layer 3) will show the verdict to the user. Calls run through the
metered one-file adapter at temperature 0.

## Question set + predictions (written BEFORE each run)

| Case | Ground truth | Prediction | Result |
|---|---|---|---|
| `shape_glued_vertical.xlsx` — invoices table, then a staff list glued directly below (2nd header at row 9) | TWO, split row 9 | two, row 9 | ✅ row 9, right reason (4/4 runs) |
| `shape_glued_control.xlsx` — ONE table with bold plain-number subtotals + grand total (the trap) | ONE | one | ✅ one (4/4 runs) |
| `shape3_multi_table.xlsx` 'Touching' — two tables glued SIDE BY SIDE (split at column D; Session-19 known code limitation) | TWO, split col D | two, col D | ✅ after 2 fix rounds (3/3 final runs) |
| Real retail workbook (6 sheets) | meanings ≈ the hand-written `sheet_meanings.json`; no false splits | match, all "one" | ✅ meanings match; 0 false splits |
| Real supplier order file (hidden Sales column) | one order table | one | ✅ + seam flag on a sparse column correctly judged ONE |
| Real stock sample file (messy sub-regions) | main list + sub-blocks | one each | ✅ plausible meanings incl. a "broken items" note block |

## The two failures and their levers (each from a failing run, per the rule)

1. **Vertical glue found at the wrong row** (said row 14, truth row 9): gluing
   poisons the column PROFILES themselves (columns turn "mixed"), so the
   suspect-row detector that trusted profiles saw nothing. **Lever:** judge
   each column by its MAJORITY type over the real rows, then flag every row
   that deviates in 2+ such columns. → row 9 found, stable.

2. **Side-by-side glue missed, then FLAKY** (verdict flipped between identical
   runs — even at temperature 0; the model's hidden thinking keeps some
   randomness): buried inside the big 3-part form, the seam question got
   judged away. **Lever (the same cure as the numbers lane):** one FOCUSED
   question per suspect seam — our code states the measured facts (which rows
   are filled on each side, the rows empty on one side) and the LLM answers
   only "one or two". A seam verdict can raise "one" to "two", never overturn
   a reported split. → 3/3 stable, and on a real file a seam flag on an
   optional sparse column was correctly answered ONE (false-positive guard
   works).

## Headline

- Dummy set: **3/3 correct and reproducible** (no-lucky-passes: 4/4, 4/4, 3/3).
- Real files: **0 false splits**, sheet meanings match the hand-written
  catalog lines the planner uses today.
- Cost per workbook (would-be, paid tier): $0.002–0.03; one LLM call per
  sheet + one tiny call per suspect seam.

## Follow-up the same day: the 14 phantom blocks → a Layer 1 merge lever

Layer 2's readings surfaced 14 small blocks on the real retail Sales sheet all
reading as the same category values. The owner confirmed those columns belong
to the MAIN table → a failing eval on real data (the condition Layer 1 reopens
under). Root cause: an always-empty column (Contact number) walls off the
table's right side, and every row that leaves "Sold by / Delivery / Type"
empty cuts the chain — the values below each cut float as fragments INSIDE the
table's own rectangle, double-reported as separate mini-tables.

**Lever:** a block completely inside another block's rectangle is a bay, not
an island — drop it (the containing region already reads those cells).

**Proof (before/after snapshots of all 17 test files):**
- 12/12 dummy shapes byte-identical — incl. the side-by-side "Separated"
  tables, which correctly survived (a genuine neighbour is never inside the
  other's rectangle).
- 4 real files changed, ALL deletion-only, all the same root cause: retail
  workbook −14 fragments (Sales = ONE table again), stock file −4, supplier
  order −1, corporate workbook −22 stray single-column helpers.
- Layer 2 re-run on the retail workbook: clean one-table readings per sheet,
  meanings unchanged, reading cost −40% (fewer regions = smaller briefs).

## Notes / still open
- Perfectly aligned side-by-side tables (same row count both sides) leave no
  fill-mismatch fingerprint — documented limitation; header meaning is then
  the only clue.
- Proposals land in `data/meaning_proposals/` — nothing writes into
  `data/sheet_meanings.json` without the user's confirmation (that is
  Layer 3's job).
