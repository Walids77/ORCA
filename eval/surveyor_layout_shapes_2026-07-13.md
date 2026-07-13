# Surveyor eval — real-world layout SHAPES (dummy files) — 2026-07-13 (Session 19)

**Method.** Scouted the research literature (DECO/Enron corpus, SpreadsheetLLM) for the
Excel layout shapes that exist in the wild → generated one neutral dummy workbook per
shape (`private/make_layout_shapes.py` → `data/layout_shapes/`), each with a written
ground truth AND a written prediction BEFORE the run → ran the surveyor (read-only,
no LLM) → graded reported structure vs ground truth. Generating (not downloading)
means we know the exact truth to grade against and there is zero privacy risk.

**Headline: 4 PASS · 1 PARTIAL · 3 FAIL — and the three fails share ONE root cause.**

| Shape | Ground truth | Predicted | Result |
|---|---|---|---|
| 3a Two tables, blank gap | 2 tables (5 + 4 rows) | pass | **PASS** — 2 tables, headers 0.96, exact rows, "2 data tables share this sheet" flagged |
| 3b Two tables, NO gap | 2 tables | fail (merge) | **FAIL (predicted)** — one 6-wide table; no warning raised. Only hint: fill-rate 80% vs 100% |
| 4 Cross-tab (months across top) | 1 table, header r1, 5 rows | structural pass | **PASS** — header r1 (0.78), 5 rows, months as columns. Left column read as plain category (axis meaning = Layer 2's job) |
| 5 Pivot-style, subtotals as PLAIN VALUES | 6 real rows; r5/r9/r10 subtotals | fail (miss subtotals) | **FAIL (predicted)** — 9 "real" rows; East/West/Grand Total counted as data → double-count risk |
| 6 Wide time-series, DATES as headers | header r1, 6 date columns named, 3 rows | weak/fail | **PARTIAL** — header r1 found (0.55), 3 rows right, but date headers dropped → 6 "(unnamed)" columns. At least loudly flagged |
| 7 Invoice document | title + 3 metadata pairs + items table (5 rows) + total formula row | mostly pass | **PASS** — title, all metadata, header r8 (0.95), total row 14 caught as derived. Wrinkles below |
| 10 Indented hierarchy, group subtotals as values | 6 city rows real; East/West = subtotals | fail | **FAIL (predicted)** — 7 "real" rows, hierarchy invisible, subtotals counted as data |
| bonus All-text table (client names/remarks) | 1 table, header r1, 6 rows | pass | **PASS** — header 0.88 with no numbers anywhere; Name/Company/City = category, Notes = free-text. Walid's question answered with evidence |

**Predictions: 8/8 correct** (every pass/fail landed where predicted — the mental model
of the surveyor is accurate).

## Diagnosis

1. **ONE root cause behind all three fails: a subtotal stored as a plain value.**
   The derived-row detector keys on FORMULAS (`=SUM(...)`). Real PivotTables and
   hand-typed subtotal rows store the number itself — no formula → invisible.
   Candidate lever (deterministic, our code, no LLM): **value-echo check** — a number
   that equals the sum of the contiguous rows above it (+ label/style hints like
   bold + "Total" in the row label) = derived. Same lever likely fixes shape 10.
2. **Touching tables merge silently** (3b). The island logic requires blank sea.
   Candidate levers: vertical seam detection (a category-text column appearing after
   numeric columns + a second styled header-like run), or at minimum a WARN when
   column fill-rates split sharply. Industry note: this is the hard case even for
   the published work (78.9% F1 overall).
3. **Date-typed header cells are not accepted as column names** (shape 6). Header
   ROW is found; the name extraction only takes TEXT cells. Cheap fix: allow
   date/number header cells, rendered as text ("2026-01"), maybe with a small score
   allowance so date headers don't drag confidence down.
4. **Invoice wrinkles (minor):** the total row is counted in BOTH "real rows" (its
   typed "Total" label) and derived — real count read 6 where 5 items exist; and the
   all-formula Amount column profiled empty because freshly GENERATED files carry no
   cached formula values (an artifact of openpyxl generation, not real uploads —
   real files opened in Excel cache their computed values).

## Levers queued (build only with Walid's go, then re-eval)
- value-echo subtotal detection (fixes shapes 5 + 10, the pivot/hierarchy family)
- date/number header names (fixes shape 6)
- derived rows excluded from the real-row count (invoice wrinkle)
- header scan deeper than 8 rows (agreed with Walid this session; no shape here hit it)
- touching-tables seam warning (hardest; maybe WARN-only first)
- font-size title signal (carried from Session 18)
