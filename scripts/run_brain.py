"""Drive ORCA's brain from the terminal and watch the notebook fill.

    ./.venv/Scripts/python.exe scripts/run_brain.py "your question here"

If no question is given, a default one about the RAG survey is used.
"""

import sys
import logging

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)  # keep the store libraries quiet

from orca.brain import build_brain

question = sys.argv[1] if len(sys.argv) > 1 else "What is Naive RAG?"

brain = build_brain()

print("Trip starts:")
print("  design:   planner (the default CPU since Session 16)")
print(f"  question: {question}\n")

final = brain.invoke({"question": question})

print("=" * 72)
print("FINAL NOTEBOOK AFTER THE TRIP")
print("=" * 72)
print(f"question:      {final['question']}")

# the planner's checklist + how the waves executed it (Session 15 design)
plan = final.get("plan", [])
if plan:
    print(f"plan:          {len(plan)} step(s), ran in {final.get('waves_run', '?')} wave(s)")
    results = final.get("step_results", {})
    for step in plan:
        n = step.get("n")
        waits = f" (waits for {step['waits_for']})" if step.get("waits_for") else ""
        print(f"  step {n} [{step.get('lane')}]{waits}: {step.get('question')}")
        r = results.get(n) or results.get(str(n)) or {}
        err = r.get("error") or (r.get("result") or {}).get("error") if isinstance(r, dict) else None
        if err:
            print(f"         ERROR: {err}")

print(f"text_hits:     {len(final.get('text_hits', []))} passages retrieved")

# what the numbers leg planned + computed (Session 13)
nums = final.get("number_result", {})
if nums.get("needed"):
    print(f"numbers leg:   computed {nums.get('computed')} from sheet {nums.get('sheet')!r}"
          + (f", filters: {nums['filters']}" if nums.get("filters") else "")
          + (f" — ERROR: {nums['error']}" if nums.get("error") else ""))
    if nums.get("sql"):
        print(f"               ran: {nums['sql']}")
print()
print("answer:")
print("-" * 72)
print(final["answer"])
