# Surveyor eval — MUTATION (injection) round — 2026-07-14 (Session 19)

**Method (Walid's idea).** Deliberately type values into known zones of a COPY of a
real file (May22 of `the real 30-sheet corporate workbook (local only, git-ignored)`) + one dummy file, and check the
surveyor reacts exactly as predicted. Zones: the SEA (blank separator space), the
ENTRY area (typed/template rows), the AGGREGATE (total rows), the HEADER.
Script: `private/mutate_and_survey.py`; mutated copies live in the session scratchpad;
originals untouched. Every prediction was written in the script BEFORE the run.
All comparisons are against a re-saved-unchanged baseline (see artifact finding).

## Scoreboard

| # | Zone / injection | Predicted | Result |
|---|---|---|---|
| M1 | SEA: lone 777 at BE950 (real file) | new tiny note region, nothing else moves | **PASS exact** — 27/27 regions unchanged + 1 note |
| M2 | TEMPLATE row: text at B60 | real rows 23→24 | **VOID (artifact)** — see finding 1; reaction was correct for the file's actual post-save state |
| M2b | ENTRY: new sale line typed at A43 (the realistic user move) | table grows to row 43, real 23→24 | **PASS exact** — A18:AF42→A18:AF43, real 24, all else untouched |
| M3 | AGGREGATE: plain 999 into total row (B20) | real +1, still derived | **SURPRISE — zero change.** Investigated: A20 holds the typed label "TOTAL", so the row was ALREADY counted both real AND derived. Extra typing changes nothing (stable), and the real+derived double-count wrinkle is confirmed LIVE on the real file |
| M4 | HEADER: D19 overwritten with a 100-char sentence | header rows hold; confidence visibly drops; column renamed | **PARTIAL** — header rows held [18,19] and the column name became the sentence (parent prefix kept), but confidence did NOT move (0.67→0.67): one bad cell among 32 barely dents the averaged signals. Robustness, but the gate gets no alarm |
| M5 | SEA: lone 42 at A20 (dummy) | new note; both tables unchanged | **PASS exact** |
| M6 | SEA bridged: D3+E3 filled (dummy) | the two tables GLUE into one | **PASS exact (glue proven)** — two typed cells collapsed A1:C6 + F1:H5 into one A1:H6 table |

Also: the first M3 attempt (U20) crashed — U20 is inside a MERGED cell (only the
top-left corner of a merged range accepts typing). Finding: total rows carry merged
cells; the mutation tooling now probes before writing.

## Findings

1. **BIG product finding — the cached-values dependency.** A `.xlsx` stores each
   formula AND its last computed value (the "cache"). openpyxl SAVES files without
   recalculating, so every formula's cached value is dropped — and the surveyor's
   values-view goes blind on formula cells: on the re-saved May22 the 854-row
   template zone vanished from the map, the dashboard fragmented into notes, and
   the main table split (H21:M42 etc. surfacing as separate regions). Files saved
   by Excel itself always carry the cache, so real user uploads are safe — but
   PROGRAMMATIC exports (scripts, some ERP/BI exporters use the same trick) are a
   real upload category. **Lever for the gate: detect "formula cells with no cached
   value" and warn — 'this file was saved by a tool, not Excel; computed values are
   invisible; open + save it in Excel once, or upload the source file'.**
2. **The real+derived double-count is live on the real file** (M3): a total row
   with a typed label is counted in BOTH piles. Same wrinkle as the invoice eval.
   Lever (already queued): derived rows must be excluded from the real-row count.
3. **Header vandalism is absorbed silently** (M4): good robustness (one bad cell
   shouldn't collapse the map) but the gate should still flag it. Lever: flag any
   header cell whose name is sentence-length (> ~40 chars) as a suspicious name.
4. **The sea is the only wall** (M6): two typed cells glue two tables. Confirms the
   touching-tables limitation from the shapes eval, from the opposite direction.
5. **The append move — the single most common real user action — works exactly
   right** (M2b), including on a file whose template zone was destroyed.

## Lever list after BOTH Session-19 evals (build only on Walid's go, then re-eval)
1. value-echo subtotal detection (shapes 5+10: pivot/hierarchy subtotals as plain values)
2. derived rows excluded from real count (finding 2 + invoice wrinkle)
3. cached-values / saved-by-a-tool warning (finding 1 — new, from the mutation round)
4. date/number header names (shape 6)
5. suspicious sentence-length header names flagged (finding 3)
6. header scan deeper than 8 rows (agreed with Walid)
7. touching-tables seam warning (hard; WARN-only first)
8. font-size title signal (carried from Session 18)
