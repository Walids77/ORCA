"""ORCA's brain — the LangGraph orchestrator.

This package is the "middle spine": it takes a question, runs it through the
retrieval legs we already built (meaning + keyword text search, and the
exact-number SQL store), then combines what came back into one answer.

We start with the SIMPLEST possible shape: one straight road, no branches, no
loops. Branches (router, decompose, calculate) get added later, one at a time,
and only if the eval says they help.
"""

from orca.brain.graph import build_brain

__all__ = ["build_brain"]
