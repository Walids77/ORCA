"""LangGraph smoke test - Walid's naive-RAG map, with NO real AI inside.

Three stations on one straight road:
    fingerprint -> search -> answer
Each station READS the notebook, does one small (fake) job,
and WRITES its result back. Run it and watch the notebook grow.

Run:  .venv\\Scripts\\python.exe scripts\\langgraph_smoke.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# 1) THE NOTEBOOK - one named entry per thing we store during the trip
class Notebook(TypedDict, total=False):
    question: str        # written in at the very start
    fingerprint: str     # node 1 writes this
    chunks: list[str]    # node 2 writes this
    answer: str          # node 3 writes this


# 2) THE STATIONS (nodes) - each is a plain Python function:
#    it receives the whole notebook, and returns ONLY the new entries it adds.
def fingerprint_node(notebook: Notebook) -> dict:
    print("  [node 1] read the question, made a (fake) fingerprint")
    return {"fingerprint": f"<vector of: {notebook['question']}>"}


def search_node(notebook: Notebook) -> dict:
    print("  [node 2] searched a (fake) vector DB using the fingerprint")
    return {"chunks": ["chunk A: Swarovski Q1 sales were ...",
                       "chunk B: the returns policy says ..."]}


def answer_node(notebook: Notebook) -> dict:
    print("  [node 3] wrote the answer from question + chunks")
    return {"answer": (f"(fake) Answer to '{notebook['question']}' "
                       f"built from {len(notebook['chunks'])} chunks")}


# 3) THE MAP - place the stations, then draw the roads between them
road_map = StateGraph(Notebook)
road_map.add_node("fingerprint", fingerprint_node)
road_map.add_node("search", search_node)
road_map.add_node("answer", answer_node)

road_map.add_edge(START, "fingerprint")     # road: start   -> node 1
road_map.add_edge("fingerprint", "search")  # road: node 1  -> node 2
road_map.add_edge("search", "answer")       # road: node 2  -> node 3
road_map.add_edge("answer", END)            # road: node 3  -> finish

brain = road_map.compile()  # lock the map so it can be driven


# 4) ONE TRIP: write the question into a fresh notebook, let it travel
print("Trip starts:")
final_notebook = brain.invoke({"question": "What were Swarovski Q1 2026 sales?"})

print("\nFinal notebook after the trip:")
for entry, value in final_notebook.items():
    print(f"  {entry}: {value}")
