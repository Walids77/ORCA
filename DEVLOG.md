# ORCA — Development Log

> Newest entry first. One dated entry per work session.

## 2026-07-03 — Session 1: Clean repo skeleton + public GitHub launch
- Initialized the fresh git repository (branch `main`) — clean history, personal identity.
- Created the Python skeleton: `src/orca/` package, `tests/`, `README.md`, `requirements.txt`.
- Built the `.gitignore` privacy fence: secrets, planning/working notes, and the local
  `data/` folder are excluded from the public repo (verified before committing).
- First commit `2e025a5` pushed to the new public repo: **github.com/Walids77/ORCA**
  (🚧 under-construction description + roadmap README).
- Added `progress.html` — a visual done-so-far timeline + the phase A–E build plan.
- Prepared `data/` (git-ignored) and received the first sample Excel for ingestion testing.
- **Next session:** Phase A — review the Excel extractor from the old ORCA baseline
  (per-file approval: copy / rewrite / skip), then ingest the sample Excel into
  SQLite + ChromaDB locally.
