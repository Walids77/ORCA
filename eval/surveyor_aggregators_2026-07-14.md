# Surveyor eval — aggregator family + small levers — 2026-07-14 (Session 19)

**What was built** (Walid's ask: extend total-detection beyond SUM + more levers + more eval):
1. **Aggregator family for plain-value rows** — the value-echo check now re-does the
   math for **SUM, AVERAGE, COUNT, MIN, MAX**. Each operation only fires on a row
   whose LABEL claims it ("Average", "Count of...", "Highest/Lowest...") — value
   coincidences are common, so the label must corroborate. Unlabelled bold rows may
   still be sums (group headers like "East"). The gate message now names the
   operation per row ("row 9 = average").
2. **Dates/years as column names** — a DATE header cell becomes "2026-01-01", a
   NUMBER one becomes "2021"; date cells also count 0.7 toward the header row's
   label-ness score.
3. **Sentence-length header flag** — a header cell over 45 characters raises
   "a column label should be short. Check the header row."
4. **Header scan deepened 8 → 15 rows** (top-bias still applies).
5. **Font-size title signal** — a small text block written at size ≥ 14 near the top
   is a title even if it isn't a lone cell (the signal `unstructured` had and we lacked).

**Deferred aggregators (need two-column reasoning — Layer 2 / later levers):**
ratios & weighted averages (May22's own dashboard has VPT = amount ÷ transactions),
percent-of-total rows, differences (Profit = Revenue − Cost), running-total COLUMNS.

## New test: `shape_agg_footer.xlsx`
A client/amount table with a 5-row plain-value footer (Total 1500 · Average 250 ·
Count of Sales 6 · Highest Sale 400 · Lowest Sale 100) and a decoy client literally
named **"Max Weber"** whose amount (350) must not be mistaken for a MAX row.

**Result: exact pass.** 6 real rows (decoy kept), all five footer rows caught with
the RIGHT operation each: row 8 = sum, 9 = average, 10 = count, 11 = max, 12 = min.

## Regression net (10 files, diff vs the previous round)
- shape6 wide time-series: **FIXED** — all six date columns named (2026-01-01…),
  header confidence 0.55 → 0.64, "unnamed" flag gone.
- shape5 / shape10: message wording only (now names the operation). Intended.
- OB7ola + updated OB7ola: **byte-identical**. shapes 3/4/7/all-text: byte-identical.
- real 30-sheet workbook: number-typed header cells got real names, which EXPOSED a
  duplicate header ("5407" twice, now flagged) — a genuine catch, not a regression.
  No title changes, no header-row moves, no false sentence-flags on any real sheet.
- Mutation suite: all 7 injections identical to the fixed round; the vandalized
  header file now ALSO raises the new flag: "header cell(s) D hold sentence-length
  text". The M4 partial from the mutation eval is closed.

## Surveyor lever board after this round
DONE: value-echo SUM/AVERAGE/COUNT/MIN/MAX · derived rows out of real counts ·
tool-saved warning · date/number header names · sentence-header flag · 15-row
header scan · font-size title.
OPEN: ratio/percent/difference rows (two-column math) · glued tables → Layer 2 (LLM
meaning + gate confirm, Walid's call) · Layer 2 itself (LLM names region meanings) ·
Layer 3 gate report · HTML rendering of surveyed regions for the vector store.
