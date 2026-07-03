"""ORCA stores — where an ingested file's data lives.

Three stores (SQLite/Chroma/local now → Postgres+pgvector/S3 later):
  - sql_store   : exact numbers, one typed table per sheet (this file).
  - vector_store: meaning / semantic search  (built later).
  - file_store  : the raw uploaded file + a manifest  (built later).
"""
