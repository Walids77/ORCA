"""The MAP — place the stations, draw the roads, hand back a driveable brain.

Straight road (no branches, no loops):

    START -> search_text -> list_numbers -> combine -> END

`build_brain` wires the real retrieval engines into the nodes and compiles the
graph. The caller just does `brain.invoke({"question": "..."})`.
"""

from langgraph.graph import StateGraph, START, END

from orca.brain.state import Notebook
from orca.brain.nodes import (
    make_search_text_node,
    make_list_numbers_node,
    llm_combine_node,
)
from orca.stores.vector_store import VectorStore
from orca.stores.hybrid import HybridSearcher
from orca.stores.sql_store import SqlStore

# Where the real, already-populated stores live (same paths the eval scripts use).
CHROMA_PATH = "data/stores/chroma"
SQL_PATH = "data/stores/orca.db"


def build_brain(company_id: str = "demo", text_file_id: str = "agentic_rag_survey"):
    """Build the straight-line brain over the real stores.

    company_id / text_file_id pick which tenant + document the text leg searches.
    The numbers leg lists all exact-number tables for the tenant.
    """
    # Real engines (MiniLM embedder is built inside VectorStore by default).
    vector = VectorStore(path=CHROMA_PATH)
    text_searcher = HybridSearcher(vector, company_id=company_id, file_id=text_file_id)
    sql = SqlStore(SQL_PATH)

    road_map = StateGraph(Notebook)
    road_map.add_node("search_text", make_search_text_node(text_searcher))
    road_map.add_node("list_numbers", make_list_numbers_node(sql))
    road_map.add_node("combine", llm_combine_node)

    road_map.add_edge(START, "search_text")
    road_map.add_edge("search_text", "list_numbers")
    road_map.add_edge("list_numbers", "combine")
    road_map.add_edge("combine", END)

    return road_map.compile()
