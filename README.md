# ORCA

**AI business assistant for retail, distribution, and operations teams** — an
agentic RAG system that reasons over documents + spreadsheets + images together
and returns exact numbers, citations, and business explanations.

> 🚧 **Status: early rebuild in progress.** This is the clean cloud rebuild of a
> working local prototype. Being built brain-first (agent orchestrator on
> LangGraph), tested locally, then deployed to AWS piece by piece.

## Roadmap
1. Agent brain (orchestrator) on LangGraph — in progress
2. Local ingestion: one Excel file → SQL rows + vectors + stored file
3. Heavy testing / eval harness in the terminal
4. Local web frontend (login · upload · ask)
5. AWS deployment (S3 · RDS + pgvector · Fargate · Cognito · Bedrock)
