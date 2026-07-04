# ORCA — Known Limitations

> Honest list of what ORCA does NOT do well yet. Each item says the limit, why it
> happens, and the planned fix. Closed items are removed (not archived).

## Ingestion

- **Visual / image-heavy PDF catalogs extract only partially.** On a real product
  catalog (`品牌`, 37 pages, mixed Chinese/English), Docling rebuilt page 1 into a
  clean table but pages 2–3 fragmented into loose text scraps. Cause: free-form,
  photo-heavy grids without clear table lines. Nothing is lost (codes/prices remain
  as searchable text), but those pages don't become clean SQL tables.
  *Fix path:* stronger table mode / OCR settings, and the Claude-oracle method
  (compare against the chatbot) — eval-graded, later.

- **PDF number-tables aren't in SQL yet.** The PDF **prose** path is done, but tables
  with numbers (purchase orders, invoices, the salary slip) are extracted and not yet
  typed + stored in SQL. *Fix path:* the table→SQL tidy stage (carry headers across
  pages, strip `$`/commas to real numbers, flag total rows — reuses the Excel logic).

## Retrieval

- **Pure semantic search is weak on "metadata" questions.** Questions like *"who are
  the authors?"*, *"what's the title?"*, *"which page/when?"* rank poorly, because a
  list of names/universities doesn't embed close to the abstract question. The right
  chunk is usually still in the top-5 (so an answer step recovers it), but ranking is
  imperfect. *Fix path (already on the roadmap):* hybrid keyword/BM25 search (brief
  #15), the stronger embedder (Bedrock Titan V2), and structured title/author metadata
  — all eval-graded.

## Testing / ops (owed, tracked in `ORCA_BRIEF.md`)

- **No formal eval harness yet** — retrieval accuracy is tested ad-hoc, not scored on a
  fixed known-answer set. This is the next build step.
- **No automated test suite / CI gate yet** — the pre-push checklist is run by hand.
- **No black-box logging or API-cost monitor yet** — only console logging; needed once
  paid APIs (Bedrock/Claude) replace the free local model.
