"""ORCA hybrid retrieval — meaning search + keyword search, merged into one list.

Semantic search (the VectorStore) finds chunks by MEANING but misses exact codes
and names ("SKU-4471", "Baccarat", an author's name). Keyword search (BM25) finds
the exact words but is blind to paraphrase. Each covers the other's weak spot, so
we run BOTH and fuse the two ranked lists with RRF (Reciprocal Rank Fusion).

RRF, plainly: a chunk's score = the sum of 1/(C + rank) over each list it appears
in (rank 1 = best). A chunk near the top of EITHER list scores well; a chunk near
the top of BOTH scores best. C controls how much a top rank in ONE list counts:
LOWER C = being #1 in one list counts for more (so a strong keyword-only hit, like
the title/authors chunk, still surfaces). No score-scaling needed — RRF uses rank
order only, which is why it's the industry default for combining different searches.

This lives ABOVE the embedder: it works the same whether the vectors came from the
local model or Titan later. Swapping the embedder does not touch this file.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from orca.stores.vector_store import VectorStore

RRF_C = 5           # ORCA's eval-tuned default (textbook standard is 60). Lower = a
                    # top rank in ONE search counts for more, so strong keyword-only
                    # hits (title/authors) surface. Validated on 2 docs, Session 6.
POOL = 20           # how many candidates to pull from each search before fusing


def _tokenize(text: str) -> list[str]:
    """Lowercase and split into words for BM25 (keeps digits + letters together)."""
    return re.findall(r"[a-z0-9]+", text.lower())


class HybridSearcher:
    """Wraps a VectorStore and adds a keyword (BM25) index over the same chunks."""

    def __init__(self, store: VectorStore, company_id: str | None = None,
                 file_id: str | None = None):
        self.store = store
        self.company_id = company_id
        self.file_id = file_id
        # Pull every chunk once and build the keyword index over their texts.
        self.chunks = store.all_chunks(company_id, file_id)
        self.by_id = {c["id"]: c for c in self.chunks}
        self.bm25 = BM25Okapi([_tokenize(c["text"]) for c in self.chunks])

    def _bm25_ranked_ids(self, query: str, n: int) -> list[str]:
        """Top-n chunk ids by keyword match, best first.

        A score of 0 means the chunk shares NO word with the query — not a real
        keyword hit. Those must not enter the fusion, or they collect RRF points
        just for occupying a rank (and with our low C, a fake rank-1 scores big).
        """
        scores = self.bm25.get_scores(_tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.chunks[i]["id"] for i in order[:n] if scores[i] > 0]

    def search(self, query: str, k: int = 5, rrf_c: int = RRF_C) -> list[dict]:
        """Hybrid search: fuse semantic + keyword results, return top-k chunks.

        rrf_c = the RRF constant. LOWER = a top rank in ONE list counts for more
        (so a strong keyword-only hit, like the title/authors chunk, still surfaces);
        HIGHER = ranks are flattened and a chunk must score in BOTH lists to win.
        """
        # List 1: meaning search (ids in best-first order).
        vec_hits = self.store.search(query, self.company_id, self.file_id, k=POOL)
        vec_ids = [h["id"] for h in vec_hits]
        # List 2: keyword search (ids in best-first order).
        kw_ids = self._bm25_ranked_ids(query, POOL)

        # RRF: add 1/(C + rank) from each list a chunk appears in.
        fused: dict[str, float] = {}
        for ranked in (vec_ids, kw_ids):
            for rank, cid in enumerate(ranked, start=1):
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_c + rank)

        top_ids = sorted(fused, key=lambda c: fused[c], reverse=True)[:k]
        return [{**self.by_id[cid], "rrf_score": fused[cid]} for cid in top_ids]
