# ORCA

**AI business assistant for retail, distribution, and operations teams** — an
agentic RAG system that reasons over documents + spreadsheets + images together
and returns exact numbers, citations, and business explanations.

> 🚧 **Status: early rebuild in progress.** This is the clean cloud rebuild of a
> working local prototype. Being built brain-first (agent orchestrator on
> LangGraph), tested locally, then deployed to AWS piece by piece.

## Roadmap
1. Local ingestion: a file → SQL rows + vectors + stored copy — **Excel done ✅ · PDF next**
2. Agent brain (orchestrator) on LangGraph
3. Heavy testing / eval harness in the terminal (incl. retrieval accuracy)
4. Local web frontend (login · upload · ask)
5. AWS deployment (S3 · RDS + pgvector · Fargate · Cognito · Bedrock)

## How ingestion works (so far)
A file enters one **doorman** that detects its type by content and routes it to a
specialist. The Excel specialist turns a workbook into three linked stores:
**SQL** (exact numbers, one typed table per sheet), **vectors** (semantic search over
each row), and a **raw file copy + manifest** — every record carries a pointer home
(sheet + row) for citations and a content hash for cheap incremental re-uploads.
