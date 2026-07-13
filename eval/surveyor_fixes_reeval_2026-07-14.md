# Surveyor re-eval — after the 3 dangerous-fix levers — 2026-07-14 (Session 19)

**What was built** (in `private/orca_secret/surveyor.py`, with Walid's go):
1. **Value-echo totals** — totals stored as PLAIN numbers (no formula — PivotTables,
   hand-typed subtotals, group headers) are caught by re-doing the math ourselves:
   a row whose number equals the sum of the contiguous rows above / everything above
   (grand total) / the rows just below (a group header above its members) is a total.
   A corroborating hint is REQUIRED (a "total/subtotal/grand/sum" label, or the row
   is styled while the table's data rows are mostly unstyled) — matching sums alone
   can be a coincidence with small numbers.
2. **Total rows leave the real-row count** — a row with aggregate formulas and no
   typed numbers is derived only, even when it carries a typed "TOTAL" label
   (the double-count trap). A record that merely carries a sum cell (running-total
   column) keeps typed numbers of its own and stays a data row.
3. **Saved-by-a-tool warning** — if most formula cells carry no computed value
   (Excel always caches results; most export tools don't), warn: values are
   invisible, open + save in Excel once and re-upload.
Plus a refined **summary-role rule**: a block is a summary only when MOST of its
distinct rows are formula-computed; a few subtotals inside a real table don't flip it.

**Method.** Before/after regression diff over all 10 files (3 real workbooks +
7 dummy shapes), then the full 7-injection mutation suite re-run.

## Results — every diff is an intended one

| File | Before | After | Verdict |
|---|---|---|---|
| shape5 pivot-style | 9 real, 0 totals | **6 real + 3 totals flagged (rows 5, 9, 10)** | FIXED as predicted |
| shape10 hierarchy | 7 real, 0 totals | **5 cities + East/West as totals** | FIXED as predicted |
| shape7 invoice | 6 real | **5 real** (= the item count) | FIXED as predicted |
| Real workbook May sheet main table | 23 real | **22 real** — matches Walid's own Session-18 count; the 23rd was the double-counted TOTAL row | FIXED (closed a Session-18 wart) |
| Real workbook other sheets | totals in real piles | totals out of real piles across all months | FIXED |
| OB7ola + updated OB7ola | 23/24 real | 22/23 real (their total row left the pile); **Summary sheet kept its summary role** | FIXED, no regression |
| shapes 3, 4, 6, all-text | — | byte-identical | no regressions |

**Regression caught & fixed mid-round:** the first version of the tightened
summary rule (totals > data rows) flipped OB7ola's Summary sheet to data-table —
on that echo-sheet many rows are records AND formula-computed. Fix: count each
row once (distinct rows) and require totals ≥ 50% of them. The before/after net
caught it immediately — this is why we capture baselines first.

**Mutation suite re-run:** all injections behave; the re-saved baseline now reads
22 real (was 23); appending a sale line gives exactly 22→23; the tool-saved warning
fires on the re-saved file ("7090 of 7090 formula cells carry no computed value").
Note: typing a plain NUMBER into the total row now re-adds that row to the real
count (typed number = record evidence) — a genuinely ambiguous state; the row keeps
its derived flag and the gate will surface it.

## Still queued (Walid's go needed, in order)
- date/number header names (shape 6 wide time-series: 6 unnamed columns)
- suspicious sentence-length header names flagged
- header scan deeper than 8 rows
- font-size title signal (Session 18 carry-over)
- glued/touching tables → moved OUT of code to Layer 2 (LLM meaning check + gate
  confirm), per Walid's call this session; code supplies the half-full-columns hint
