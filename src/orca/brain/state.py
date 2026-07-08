"""The Notebook — the shared state every node reads from and writes to.

LangGraph passes ONE object down the road; each station reads what it needs and
writes back only the new entries it produced. This TypedDict just names the
slots so the whole trip is easy to follow.
"""

from typing import TypedDict


class Notebook(TypedDict, total=False):
    # written in at the very start
    question: str

    # the TEXT leg (meaning + keyword search, already fused by HybridSearcher)
    # writes this: a list of retrieved chunks, each = {id, text, metadata, ...}
    text_hits: list[dict]

    # the NUMBERS leg (SQL store) writes this: the exact-number tables that exist
    # for this tenant, so we know what could be queried. Each = {sheet, columns, ...}
    number_tables: list[dict]

    # the COMBINE station writes the final answer here
    answer: str
