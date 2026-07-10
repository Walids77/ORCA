# Excel data-entry & layout best practices for RAG systems

> Every rule on this list was earned, not copied: each one traces to a real
> failure ORCA's evals caught during ingestion and question-answering sessions.
> Follow these when preparing spreadsheets for ANY RAG / AI-assistant system —
> the cleaner the sheet, the more questions the assistant can answer exactly.
> (This list also feeds ORCA's data-quality advisor: when ORCA can't answer
> because the source breaks one of these rules, it should say WHICH rule and
> how to fix the sheet — see the roadmap.)

## Layout rules (how the sheet is shaped)

1. **One table per sheet.** Never park a second mini-table below or beside the
   main one — a parser reads columns by position, and a second table poisons
   the column types. *(Found in ingestion: a mini-table under the Expenses data
   had to be detected and fenced off by column-type analysis.)*
2. **One header row, every column named.** No merged cells, no two-row headers,
   no unnamed columns — each column name becomes a database field the AI can
   query by.
3. **A row = one record (one sale, one order, one expense).** Don't stack two
   facts in one row or spread one fact across two rows.
4. **Label every total/summary row explicitly** — put the word "Total" in the
   label column. An unlabelled total row gets counted as data and silently
   DOUBLES every sum. *(Our single most dangerous bug: unlabelled total rows
   inflated aggregates until a 3-detector fix — label, formula-reading, shape —
   caught them. Even the human answer key had inherited the doubled figure.)*
5. **Don't carry meaning in formatting.** Bold, color, and borders are
   invisible to a parser. If a row is special (a return, a correction, a
   total), say so in a column.

## Data-entry rules (what goes in the cells)

6. **Separate facts get separate columns.** The big one: don't bury item
   names, client names, or categories inside a free-text remark. Add an
   "Item" / "Client" / "Category" column. *(Real cost: "what did clients buy
   in February?" required detective work over remark text because items only
   existed inside remarks. "Which client bought most?" is UNANSWERABLE exactly
   without a client column — remarks can describe, never rank.)*
7. **Real date cells, one consistent format, one date column.** Text
   pretending to be a date (or a stray 1900 date) breaks month filtering.
   *(Our quality scan found year-1900 dates and text sitting in a date
   column — 14 real problems in one workbook.)*
8. **Numbers are numbers.** No "$", no thousands-commas, no "N/A" text inside
   a numeric column — one currency per column (name it in the header:
   "Net Sales USD").
9. **Consistent names.** The same client/supplier/product spelled the same way
   every time — "Acme" and "Acme Co." are two different suppliers to a
   database.
10. **Keep formulas simple and vertical** (a SUM over the rows above it), or
    better: label computed rows (rule 4). Cross-sheet and sideways formulas
    make totals hard to verify.

## Naming rules (what things are called)

11. **Name each sheet by its business meaning** — "Sales", "Expenses",
    "Client Deposits". The assistant's catalog shows these names to the AI
    planner; a sheet called "Sheet3" gives it nothing to reason with.
12. **One meaning per sheet.** If a sheet mixes client purchases with company
    purchases, "what was bought?" becomes ambiguous — the AI can pick the
    wrong table with full confidence. *(Live example: "what was bought in
    December?" was answered from company Expenses instead of client Sales —
    the words were similar, the meaning wasn't.)*

## Why this matters (the one-line version)
A RAG system turns your spreadsheet into a database it can query exactly.
Every rule above protects one link in that chain: layout rules protect the
PARSING, entry rules protect the VALUES, naming rules protect the AI's
UNDERSTANDING of what it may query. Break a rule and the failure is silent —
the assistant answers less, or worse, answers wrong.
