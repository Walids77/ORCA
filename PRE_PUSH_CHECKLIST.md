# ORCA — Pre-Push Checklist

> Run BEFORE every `git push`. ORCA is a **PUBLIC** repo — check #1 is the one
> that can never be skipped. Ported from GoFetch's discipline, levelled up for
> ORCA. Goal: checks 2–4 become a GitHub Actions CI gate (a robot on GitHub that
> runs the tests itself and physically blocks a red push) — until then, this
> list is run by hand every time.

## 1. Secrets & private-data scan (NEVER SKIP — public repo)
- [ ] No API keys, passwords, or tokens anywhere in the diff (`.env` stays
      git-ignored; grep the staged changes for `key`, `secret`, `token`, `sk-`, `AIza`).
- [ ] No real business data: client names, sales figures, supplier names, the
      real Excel/PDF files. `data/` stays git-ignored; eval files that quote real
      rows (e.g. Session-13's numbers eval) stay git-ignored until the neutral
      demo corpus exists.
- [ ] No CV / personal documents / personal plan files (the `.gitignore` fence).
- [ ] `git status` reviewed line by line — nothing unexpected staged.

## 2. Tests green
- [ ] Run the test suite (pytest, once built — until then: the current session's
      smoke scripts). All green. NEVER weaken or delete a failing test to make it
      pass; if behavior changed on purpose, update the test AND tell Walid why.

## 3. One real end-to-end
- [ ] Ask one known-answer question through the real pipeline (real file → real
      stores → real answer) and confirm the answer matches the key. Not a mock.

## 4. Evals recorded
- [ ] If an eval ran this session: its dated record exists in `eval/`
      (question set · method · per-question verdict · headline number ·
      diagnosis + fix). Standing rule: never run an eval without saving the record.

## 5. Graceful failure
- [ ] The changed path fails politely on bad input (no stack trace to the user;
      "NO DATA" / refusal wording where evidence is missing).

## 6. Cost sanity
- [ ] New/changed LLM calls go through the one-file adapter (`llm.py`) — never a
      direct API call from a node. Token/cost meter (item #20) counts them once built.

## 7. Docs in sync
- [ ] `progress.html` ticked + "NOW" marker advanced; `DEVLOG.md` entry if the
      session ends here; `ORCA_BRIEF.md` checklist/Next-action current.
