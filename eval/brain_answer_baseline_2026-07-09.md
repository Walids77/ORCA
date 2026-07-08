# Brain answer-eval — BASELINE (2026-07-09, Session 12)

> **First ANSWER-level eval.** Earlier evals (43% → 87.5%) graded *retrieval* only
> ("did the right chunk land in the top 5?"). This one grades the **final answer**
> the brain writes, end-to-end: `question → text leg (hybrid) → numbers leg → combine (Gemini)`.
>
> - Brain: the straight-line skeleton (`src/orca/brain/`), no branches, no loop.
> - Text leg: `HybridSearcher`, top-5 chunks, on the Agentic-RAG survey (arXiv 2501.09136).
> - Thinking node: Gemini `gemini-2.5-flash` (temporary), instructed to answer ONLY from the
>   retrieved passages and to refuse ("I can't answer that from the uploaded documents.")
>   when the evidence isn't there.
> - Grading = first-pass by Claude; **to be reviewed WITH Walid next session** (answer
>   correctness is a judgment call — the ⚠️ rows especially).

## Headline
**≈13–15 / 20 correct (~65–75%).** All 3 not-in-doc traps correctly refused. The metadata
questions that ALL failed at the 43% baseline (authors · title · GitHub) now PASS at the
answer level — the hybrid-BM25 work paying off. Failures cluster in two clean piles (below).

## Per-question records + recommended fix

| Q | Question | Verdict | Diagnosis | Recommended fix |
|---|---|---|---|---|
| 1 | What is Naive RAG? | ✅ | grounded, cited [1] | — |
| 2 | Three core components of RAG? | ✅ | Retrieval/Augmentation/Generation | — |
| 3 | Four agentic **design** patterns? | ❌ refused | enumerating chunk not in top-5 (Reflection/Planning/Tool-Use each own chunk) | **Pile 1**: raise k / reranker; test the loop |
| 4 | Modular vs Naive RAG? | ✅ | excellent, grounded | — |
| 5 | Agentic Corrective RAG? | ✅ | detailed, matches §5.4 | — |
| 6 | Name three **workflow** patterns | ⚠️ wrong category | answered §3 *design* patterns, not §4 *workflow* patterns (prompt-chaining/routing/…) | **Pile 2**: retrieval precision; a term-aware router later |
| 7 | Primary bottleneck in RAG quality? | ✅ | "retrieval quality", cited | — |
| 8 | Tools/frameworks for Agentic RAG? | ❌ refused | right page (31) retrieved but not the framework-list chunk | **Pile 1**: reranker / better chunk targeting |
| 9 | Application domains covered? | ⚠️ thin | only named what 5 chunks held; domains are scattered | **Pile 1 (gather)**: raise k so scattered evidence is unified |
| 10 | Taxonomy categories? | ⚠️ partial | gave single/multi/graph families | retrieval precision; see Q15 tension |
| 11 | Authors? | ✅ | correct — **metadata win** | — |
| 12 | Title? | ✅ | correct — **metadata win** | — |
| 13 | Page the Agentic-RAG paradigm appears? | ❌ | said p8, truth p6 | **Pile 2**: trusted a plausible wrong chunk |
| 14 | GitHub repository? | ✅ | survey's own repo returned first — **footnote fix works** (extra repos = noise) | (tighten: answer the paper's OWN repo only) |
| 15 | How many taxonomy categories? | ❌ | said 4 (named dimensions), truth 7 | **Pile 2**: wrong chunk trusted |
| 16 | HumanEval accuracy? (NOT IN DOC) | ✅ | correctly refused | — |
| 17 | Fine-tuning/RLHF recommendation? (NOT IN DOC) | ✅ | correctly refused | — |
| 18 | GPU hardware/pricing? (NOT IN DOC) | ✅ | correctly refused | — |
| 19 | Compare Traditional vs Agentic RAG | ✅ | matches Table 2, p29 | — |
| 20 | Naive vs Advanced RAG? | ✅ | excellent, grounded | — |

## The two failure piles (this is what drives the next build step)

**Pile 1 — refused / thin, but the doc CAN answer** (Q3, Q8, Q9).
The right chunk didn't reach the top 5, so the thinking step had nothing to answer from.
→ Fix candidates, cheapest first: **(a) raise k** (retrieve more, one pass); **(b) a reranker**
(needs a model); **(c) the corrective loop** (retrieve → judge "enough?" → reword query → retry,
capped). Per Walid's rule: try the cheap one-pass fix first, only earn the loop if the eval proves
one pass can't do it.

**Pile 2 — answered CONFIDENTLY WRONG** (Q6, Q13, Q15). The more dangerous pile.
Retrieval handed over a *plausible-looking wrong chunk* and the thinking step trusted it.
→ Fix candidates: **retrieval precision** (reranker) + an **answer self-check** node
(the back-guard in the target map). These are wrong even though a human would spot them, so
they matter more than the polite refusals in Pile 1.

## Wins to keep
- **Guardrail solid:** 3/3 not-in-doc traps refused — no hallucination.
- **Metadata now works:** authors, title, GitHub all pass (were 0/5 at the 43% baseline).
- **Grounding + citations** present on the correct answers ([1], [2]…).

## Next session
Review these answers WITH Walid, confirm/adjust the grades, then decide the first refinement to
test — almost certainly **raise k** (cheap, one-pass) against Pile 1 first, re-run this exact
eval, and see if it out-grades this baseline before reaching for the reranker or the loop.
