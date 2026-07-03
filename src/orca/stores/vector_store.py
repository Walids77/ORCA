"""ORCA vector store — the MEANING / semantic-search home.

Each row becomes a short text chunk + an embedding (a "meaning fingerprint"), so
ORCA can find rows by concept, not just exact words. Every chunk carries its
pointer home (company / file / sheet / Excel row) for tenant filtering + citations.

ChromaDB now → Postgres + pgvector later. The EMBEDDER is swappable:
  - default here = Chroma's built-in local model (all-MiniLM-L6-v2, free, offline)
    — a stand-in to prove the plumbing;
  - later = Amazon Titan V2 on Bedrock (the real, eval-graded model) — a one-line
    swap by passing a different `embedder`.
"""

from __future__ import annotations

import logging

import chromadb
from chromadb.utils import embedding_functions

from orca.ingest.records import build_chunks

logger = logging.getLogger(__name__)


def _tenant_filter(company_id: str | None, file_id: str | None):
    """Build a Chroma 'where' filter for tenant / file isolation."""
    conds = []
    if company_id:
        conds.append({"company_id": company_id})
    if file_id:
        conds.append({"file_id": file_id})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


class VectorStore:
    """A thin wrapper over one persistent Chroma collection."""

    def __init__(self, path: str, collection: str = "orca", embedder=None):
        self.client = chromadb.PersistentClient(path=path)
        # Swap this line to move to Titan/Bedrock later; nothing else changes.
        ef = embedder or embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection, embedding_function=ef,
        )

    def store_workbook(self, company_id: str, file_id: str, extract) -> int:
        """Embed + store every chunk of a workbook. Returns the chunk count.

        Wholesale-replaces this file's chunks. With the free local model that's
        cheap; when we move to a PAID embedder we'll switch to hash-diffing (only
        re-embed changed rows) using the row_hash already stored on each chunk.
        """
        chunks = build_chunks(extract, company_id, file_id)
        self.collection.delete(where=_tenant_filter(company_id, file_id))
        if chunks:
            self.collection.add(
                ids=[c["id"] for c in chunks],
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
            )
        logger.info("Embedded %d chunk(s) for %s/%s", len(chunks), company_id, file_id)
        return len(chunks)

    def search(self, query: str, company_id: str | None = None,
               file_id: str | None = None, k: int = 5) -> list[dict]:
        """Semantic search. Returns the top-k chunks with their pointer-home metadata."""
        res = self.collection.query(
            query_texts=[query], n_results=k,
            where=_tenant_filter(company_id, file_id),
        )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0],
                                   res["distances"][0]):
            hits.append({"text": doc, "metadata": meta, "distance": dist})
        return hits

    def count(self) -> int:
        return self.collection.count()
