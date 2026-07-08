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
print(f"  question: {question}\n")

final = brain.invoke({"question": question})

print("=" * 72)
print("FINAL NOTEBOOK AFTER THE TRIP")
print("=" * 72)
print(f"question:      {final['question']}")
print(f"text_hits:     {len(final.get('text_hits', []))} passages retrieved")
print(f"number_tables: {len(final.get('number_tables', []))} exact-number tables")
print()
print("answer (plain stitch — no AI yet):")
print("-" * 72)
print(final["answer"])
