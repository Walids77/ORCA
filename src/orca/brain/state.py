"""The Notebook — the shared state every node reads from and writes to.

LangGraph passes ONE object down the road; each station reads what it needs and
writes back only the new entries it produced. This TypedDict just names the
slots so the whole trip is easy to follow.
"""

from typing import TypedDict


class Notebook(TypedDict, total=False):
    # written in at the very start
    question: str

    # the ROUTER (Session 14) writes these: which lane(s) to run, plus a
    # FOCUSED sub-question per leg — compound questions get split here so each
    # leg sees only its own half (the run-1/run-2 evidence: the one-shot
    # numbers form coin-flips on compound questions)
    lane: str                 # "text" | "numbers" | "both"
    text_question: str
    numbers_question: str

    # the TEXT leg (meaning + keyword search, already fused by HybridSearcher)
    # writes this: a list of retrieved chunks, each = {id, text, metadata, ...}
    text_hits: list[dict]

    # the NUMBERS leg (SQL store) writes this: the LLM's query plan + the exact
    # result our code computed (or {"needed": False} for non-number questions)
    number_result: dict

    # the COMBINE station writes the final answer here
    answer: str
