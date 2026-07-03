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

## How this was built
**Designed and directed by Walid Semaan — the system designer.** Walid defines the
architecture and creates the logic, brings his own research, and drives every decision.
The working method: Claude Code (AI) suggests options and implements the chosen approach
in code; Walid reviews the options and picks the direction, tests each result, and makes
the final call on the product. In short — **Walid designs the system and owns the
decisions; the AI writes the code under his direction and review.**
