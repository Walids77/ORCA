"""The MAP — place the stations, draw the roads, hand back a driveable brain.

Three designs (Session 14 — the eval compares them on the same question set):

  "router":            START -> router -> (conditional junction)
                                  text lane / numbers lane / both lanes
                                          \\        /
                                           combine -> END
  The router reads the tenant's catalogs, picks the lane(s), and hands each
  chosen leg a FOCUSED sub-question (compound questions get split). Unreadable
  router reply -> falls back to "both" = the parallel design.

  "straight"  (Sessions 12–13)          "parallel"  (Session 14 — fan-out/fan-in)

  START -> search_text                        START
             -> answer_numbers               /      \\
               -> combine -> END      search_text  answer_numbers
                                             \\      /
                                             combine -> END

In the parallel design LangGraph runs both legs AT THE SAME TIME and only
starts `combine` once BOTH have written to the notebook (the fan-in wait is
the framework's job). No notebook clash: each leg writes its OWN page
(`text_hits` vs `number_result`), so nothing needs merging.

`build_brain` wires the real retrieval engines into the nodes and compiles the
graph. The caller just does `brain.invoke({"question": "..."})`.
"""

from langgraph.graph import StateGraph, START, END

from orca.brain.state import Notebook
from orca.brain.nodes import (
    make_router_node,
    make_search_text_node,
    make_answer_numbers_node,
    llm_combine_node,
    plan_combine_node,
)
from orca.brain.numbers import load_catalog, catalog_text
from orca.brain.planner import make_planner_node
from orca.brain.runner import make_plan_runner_node, more_waves
from orca.stores.vector_store import VectorStore
from orca.stores.hybrid import HybridSearcher
from orca.stores.sql_store import SqlStore

# Where the real, already-populated stores live (same paths the eval scripts use).
CHROMA_PATH = "data/stores/chroma"
SQL_PATH = "data/stores/orca.db"


def build_brain(
    company_id: str = "demo",
    text_file_id: str | None = None,
    design: str = "parallel",
    allowed_files: set[str] | None = None,
):
    """Build the brain over the real stores, in the requested wiring.

    design="parallel" (default): both legs fan out from START and combine
    fans them back in — same stations, same accuracy, less waiting.
    design="straight": the Sessions-12/13 sequential wiring, kept selectable
    so the eval comparison stays reproducible.

    Session 13: text_file_id now defaults to None = the text leg searches ALL of
    the tenant's documents (survey PDF + the Excel's row-chunks together). Facts
    living in free text — like client names inside a sales remark — are only
    findable this way. Pass a file_id to narrow to one document (the evals do).

    Session 15: allowed_files = the RBAC fence. When set, both catalogs the
    router/planner LLM ever sees (spreadsheet menu + text-doc list) are filtered
    to these files by OUR code before any prompt is built — the LLM never picks
    its own catalog. None = no restriction (single-user today); the multi-user
    layer later computes this set per role at login.
    """
    # Real engines (MiniLM embedder is built inside VectorStore by default).
    vector = VectorStore(path=CHROMA_PATH)
    text_searcher = HybridSearcher(vector, company_id=company_id, file_id=text_file_id)
    sql = SqlStore(SQL_PATH)

    road_map = StateGraph(Notebook)

    if design == "planner":
        # Session 15: START -> planner -> plan-runner (capped loop, one lap =
        # one WAVE of parallel steps) -> combine. The planner writes the
        # checklist; the runner executes it through the same proven legs. This
        # design has its own stations, so it draws its own map and returns.
        menu_catalog = load_catalog(sql, company_id, allowed_files)
        menu = catalog_text(menu_catalog)
        doc_titles = sorted({
            (c.get("metadata") or {}).get("doc_title")
            for c in text_searcher.chunks
            if (c.get("metadata") or {}).get("doc_title")
            and (allowed_files is None
                 or (c.get("metadata") or {}).get("file_id") in allowed_files)
        })
        doc_list = "\n".join(f"- {t}" for t in doc_titles) or "- (uploaded documents)"
        road_map.add_node("planner", make_planner_node(menu, doc_list))
        road_map.add_node("run_wave",
                          make_plan_runner_node(text_searcher, sql,
                                                menu_catalog, menu))
        # The planner-design combine reads the whole checklist's results.
        road_map.add_node("combine", plan_combine_node)
        road_map.add_edge(START, "planner")
        road_map.add_edge("planner", "run_wave")
        road_map.add_conditional_edges(
            "run_wave", more_waves, {"again": "run_wave", "done": "combine"}
        )
        road_map.add_edge("combine", END)
        return road_map.compile()

    road_map.add_node("search_text", make_search_text_node(text_searcher))
    road_map.add_node("answer_numbers",
                      make_answer_numbers_node(sql, company_id, allowed_files))
    road_map.add_node("combine", llm_combine_node)

    if design == "straight":
        # Sequential: the numbers leg waits for the text leg for no reason.
        road_map.add_edge(START, "search_text")
        road_map.add_edge("search_text", "answer_numbers")
        road_map.add_edge("answer_numbers", "combine")
    elif design == "router":
        # Router first (domain-first, reads both catalogs), then a conditional
        # junction: only the picked lane(s) run. Chosen legs still run in
        # parallel when the lane is "both".
        menu = catalog_text(load_catalog(sql, company_id, allowed_files))
        # Same RBAC fence on the text-document list the router sees.
        doc_titles = sorted({
            (c.get("metadata") or {}).get("doc_title")
            for c in text_searcher.chunks
            if (c.get("metadata") or {}).get("doc_title")
            and (allowed_files is None
                 or (c.get("metadata") or {}).get("file_id") in allowed_files)
        })
        doc_list = "\n".join(f"- {t}" for t in doc_titles) or "- (uploaded documents)"
        road_map.add_node("router", make_router_node(menu, doc_list))
        road_map.add_edge(START, "router")

        def pick_lanes(notebook: Notebook) -> list[str]:
            lane = notebook.get("lane", "both")
            if lane == "text":
                return ["search_text"]
            if lane == "numbers":
                return ["answer_numbers"]
            return ["search_text", "answer_numbers"]

        road_map.add_conditional_edges(
            "router", pick_lanes, ["search_text", "answer_numbers"]
        )
        road_map.add_edge("search_text", "combine")
        road_map.add_edge("answer_numbers", "combine")
    else:
        # "parallel" — fan-out: both legs leave START together; fan-in: combine
        # waits for both.
        road_map.add_edge(START, "search_text")
        road_map.add_edge(START, "answer_numbers")
        road_map.add_edge("search_text", "combine")
        road_map.add_edge("answer_numbers", "combine")
    road_map.add_edge("combine", END)

    return road_map.compile()
