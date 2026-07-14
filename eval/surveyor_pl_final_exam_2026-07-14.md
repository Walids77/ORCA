# Surveyor — P&L finance sheet, Layer 1 final exam — 2026-07-14 (Session 20)

**The exam.** A generated income statement (`data/layout_shapes/shape_pl_finance.xlsx`,
generator `private/make_finance_shape.py`) modeled on how accounting tools export
one — the hardest proven shape: every number a PLAIN VALUE (no formulas), indented
sections, bare year numbers (2025 / 2024) as column headers, "Total …" subtotal
rows, and profit rows that are DIFFERENCES (Gross Profit = Revenue − COGS), which
no lever computed. Internally consistent to the cent. Predictions written first.

## First run — 4 findings (3 predicted, 1 cascade surprise)

| Finding | Predicted? |
|---|---|
| Header landed on the bold "Revenue" section row — bare year NUMBERS earn no header credit (text/dates only), so the year row lost | yes (named as a risk) |
| "Gross Profit" / "Operating Income" (differences) invisible — the Session-19 deferred lever's failing eval | yes |
| **Cascade:** "Total Operating Expenses" ALSO missed — the uncaught Gross Profit row sat inside its comparison stretch and poisoned the full-segment sum check | **no — new find** |
| "Net Income" missed: no "Total" label + the bold-row fallback correctly refuses on bold-HEAVY sheets (every section header is bold) | yes, wrong mechanism predicted |

## The three levers built (Walid's go)

1. **Years count as header labels** — a bare integer 1900–2100 in a candidate
   header row earns date-like credit (textness, shortness, and contrast over a
   clean number column). Header now row 4, confidence 0.58 → 0.79, columns named
   "2025" / "2024".
2. **Profit pass (chain + difference), label-gated** (profit/income/net/margin/
   earnings/ebit/loss): a row is computed if its value equals (a) the nearest
   computed row above + the plain rows between them ("carries the total above
   forward" — Net Income = Operating Income + negative tax), or (b) one earlier
   computed row minus another (Gross Profit = Total Revenue − Total COGS).
3. **Nearest-rows sum matching** — the value-echo SUM check now tests at every
   step walking up (nearest rows first), so one uncaught row can't poison the
   next total's detection.

**Coincidence caught mid-round (the net working):** the first profit-pass version
marked "Income Tax" as computed — its 2024 value (−25,000) accidentally equals
Total OpEx − Total COGS in that one column. Fix: a REAL P&L relationship holds in
EVERY number column of the row (2025 AND 2024); require all columns to agree.
Income Tax's 2025 column matches nothing → correctly back in the real pile.

## Final result — full marks

- header row 4 (the years), confidence 0.79; columns "(unnamed A)" · "2025" · "2024"
- computed rows = exactly the six true ones: Total Revenue · Total COGS ·
  Gross Profit (difference) · Total Operating Expenses · Operating Income
  (difference) · Net Income (carry-forward) — with plain-English reasons in the
  gate message
- real rows = the 8 line items (incl. Income Tax) + 3 section headers (typed
  rows; naming their meaning = Layer 2's job)

## Regression proof
- Before/after net over the 11 prior files: **byte-identical**.
- Session-19 mutation suite re-run: all injections behave as baseline.
- `shape_pl_finance.xlsx` joins the permanent corpus (now 13 files with
  `shape_photos.xlsx`).

**Layer 1 is CLOSED — final exam passed.** Reopens only on a failing eval.
