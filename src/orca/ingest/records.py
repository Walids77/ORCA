"""Row fingerprints — the stable ID that makes incremental updates possible.

Each Excel row gets a short hash of its content. When a file is re-uploaded:
  - a row whose hash still exists  -> unchanged (reuse it, don't re-embed)
  - a hash that disappeared        -> the row was edited or deleted (drop it)
  - a hash that is new             -> the row was added (insert + embed it)

Hashing the CONTENT (not the position) means an edited row automatically looks
like "old row gone, new row arrived" — no fragile primary-key guessing needed.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> Any:
    """Turn a cell value into a stable, JSON-friendly form for hashing."""
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)          # 41.0 and 41 should hash the same
    return value


def row_fingerprint(sheet_name: str, row: dict[str, Any]) -> str:
    """A short, stable hash of one row's content (same content -> same hash)."""
    items = sorted((str(k), _canonical(v)) for k, v in row.items())
    payload = sheet_name + "|" + json.dumps(items, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# STAGE 6 - build the searchable text chunks (the "meaning" side)
# =============================================================================
def _fmt(value: Any) -> str:
    """Render a cell value for the chunk text (dates as plain YYYY-MM-DD)."""
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    return str(value)


def build_chunks(extract, company_id: str, file_id: str) -> list[dict]:
    """Turn a workbook into vector chunks: one per data row + one per side block.

    Each chunk = a readable line of text + metadata that points HOME
    (company / file / sheet / Excel row / row_hash) for tenant filtering,
    incremental updates, and citations.
    """
    chunks: list[dict] = []
    for sheet in extract.sheets:
        agg = set(sheet.aggregate_rows)
        for i, row in enumerate(sheet.rows):
            parts = [f"{col}: {_fmt(v)}" for col, v in row.items() if v is not None]
            if not parts:
                continue
            chunks.append({
                "id": f"{company_id}:{file_id}:{sheet.sheet_name}:{sheet.source_rows[i]}",
                "text": f"[{sheet.sheet_name}] " + ", ".join(parts),
                "metadata": {
                    "company_id": company_id, "file_id": file_id,
                    "sheet": sheet.sheet_name, "source_row": sheet.source_rows[i],
                    "row_hash": row_fingerprint(sheet.sheet_name, row),
                    "is_total": i in agg,
                },
            })
        # side blocks (e.g. "Fast Calculation") — searchable context, not SQL data
        for aux in sheet.aux_blocks:
            chunks.append({
                "id": f"{company_id}:{file_id}:{sheet.sheet_name}:aux:{aux.start_row}",
                "text": f"[{sheet.sheet_name} — note] {aux.text}",
                "metadata": {
                    "company_id": company_id, "file_id": file_id,
                    "sheet": sheet.sheet_name, "source_row": aux.start_row,
                    "row_hash": "", "is_total": False, "is_aux": True,
                },
            })
    return chunks


# =============================================================================
# PDF PROSE CHUNKER - turn a PdfExtract's text blocks into searchable chunks
# =============================================================================
# The prose path: structure-aware, heading-grouped chunks of ~500 tokens with a
# ~12% overlap. This is the 2026 best-practice shape (recursive/structure-aware +
# overlap + a metadata card), and it is deliberately OUR own transparent code so
# we can read it and eval-grade it (Docling's built-in HybridChunker is kept as a
# later comparison). Tables are NOT handled here — they go to the table→SQL stage.

# Docling block labels that are NOISE for retrieval — dropped before chunking.
_PDF_NOISE_LABELS = {"page_header", "page_footer", "footnote", "caption"}

# Target chunk size + overlap, measured in ESTIMATED tokens (~4 chars per token).
_TARGET_TOKENS = 500
_OVERLAP_TOKENS = 60            # ~12% of the target
_CHARS_PER_TOKEN = 4

# Sentence boundary: a . ! or ? followed by whitespace. Used only to break a
# single paragraph that is bigger than one chunk, so no chunk is oversized.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _estimate_tokens(text: str) -> int:
    """Rough token count (~4 characters per token).

    A deliberate approximation — good enough for sizing chunks, and swappable for
    a real tokenizer later when we eval chunk sizing.
    """
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _slug(text: str) -> str:
    """A short, filename-safe id made from a heading (for the parent id)."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "none"


def _split_oversize(text: str) -> list[str]:
    """Split one block into <=target-size pieces on sentence boundaries.

    Only kicks in when a single paragraph is already bigger than one chunk — so a
    giant block never becomes a giant chunk (which hurts retrieval quality).
    """
    if _estimate_tokens(text) <= _TARGET_TOKENS:
        return [text]
    out: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for sentence in _SENTENCE_SPLIT.split(text):
        st = _estimate_tokens(sentence)
        if cur_tokens + st > _TARGET_TOKENS and cur:
            out.append(" ".join(cur))
            cur, cur_tokens = [], 0
        cur.append(sentence)
        cur_tokens += st
    if cur:
        out.append(" ".join(cur))
    return out


def _overlap_tail(pieces: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Return the trailing pieces of a chunk that sum to ~the overlap size.

    These get carried into the NEXT chunk so a fact sitting on the boundary is not
    lost between two chunks.
    """
    tail: list[tuple[str, int]] = []
    tokens = 0
    for piece in reversed(pieces):
        tail.insert(0, piece)
        tokens += _estimate_tokens(piece[0])
        if tokens >= _OVERLAP_TOKENS:
            break
    return tail


# --- telling a REAL section heading from a mis-tagged one (author / title) ----
# Docling tags author names and the paper title as "section_header" too, and it
# gives every heading the same level, so we can't trust the label alone. A heading
# is REAL if it is numbered ("2.1 ...") or a known structural word (ABSTRACT,
# INTRODUCTION...), OR if it actually has body text under it. A "heading" with
# almost no text under it (e.g. an author name followed by one affiliation line)
# is front-matter noise, not a section.
_MIN_SECTION_TOKENS = 40
# Safety cap: if we collect this many tokens of "front matter" without ever
# hitting a real heading (an odd doc with no headings), stop — so we never dump a
# whole document into one front-matter chunk.
_FRONTMATTER_CAP = 300
_REAL_HEADING_WORDS = {
    "abstract", "introduction", "conclusion", "conclusions", "references",
    "acknowledgments", "acknowledgements", "appendix", "keywords", "summary",
    "discussion", "background", "related work", "methodology", "results",
}
_NUMBERED_HEADING = re.compile(r"^\s*\d+(\.\d+)*[\s.]")


def _is_real_heading(heading: str) -> bool:
    """True if this heading is clearly a real section (numbered or a known word)."""
    if _NUMBERED_HEADING.match(heading):
        return True
    return heading.strip().lower() in _REAL_HEADING_WORDS


def _emit_frontmatter(out: list[dict], title: str, pieces: list[tuple[str, int]],
                      company_id: str, file_id: str) -> None:
    """Emit the title + authors + affiliations as ONE clean chunk.

    So "who is the author?" / "what is the title?" retrieve a single coherent
    chunk instead of the authors being scattered into fake one-line sections.
    """
    if not title and not pieces:
        return
    # Enrich the embedded text with natural-language cues ("authors", "who wrote
    # this") so a question like "who are the authors?" matches — a bare list of
    # names + universities does NOT embed close to that question on its own.
    names_and_affiliations = " ".join(t for t, _ in pieces).strip()
    parts = ["[Title & authors]"]
    if title:
        parts.append(f"Title: {title}.")
    parts.append("Authors (the people who wrote this document) and their affiliations:")
    if names_and_affiliations:
        parts.append(names_and_affiliations)
    idx = len(out)
    out.append({
        "id": f"{company_id}:{file_id}:pdf:{idx}",
        "text": " ".join(parts).strip(),
        "metadata": {
            "company_id": company_id, "file_id": file_id, "source": "pdf",
            "section": "Front matter (title & authors)",
            "parent_id": f"{company_id}:{file_id}:sec:frontmatter",
            "page": 1, "pages": "1", "section_page": 1, "chunk_index": idx,
            "doc_title": title or "", "is_frontmatter": True,
        },
    })


def _emit_section_chunks(out: list[dict], pieces: list[tuple[str, int]], section: str,
                         section_page: int, doc_title: str,
                         company_id: str, file_id: str) -> None:
    """Pack one section's pieces into overlapping ~target-size chunks."""
    parent_id = f"{company_id}:{file_id}:sec:{_slug(section)}"   # hierarchical-ready
    cur: list[tuple[str, int]] = []
    cur_tokens = 0

    def flush() -> None:
        nonlocal cur, cur_tokens
        if not cur:
            return
        body = " ".join(p[0] for p in cur).strip()
        pages = sorted({p[1] for p in cur})
        idx = len(out)
        out.append({
            "id": f"{company_id}:{file_id}:pdf:{idx}",
            # prepend the heading so the embedding "sees" what section this is from
            "text": (f"[{section}] " + body) if section else body,
            "metadata": {
                "company_id": company_id, "file_id": file_id,
                "source": "pdf",
                "section": section or "(none)",
                "section_page": section_page,      # page the heading appears on
                "doc_title": doc_title,            # for citations across every chunk
                "parent_id": parent_id,
                "page": pages[0],
                "pages": ",".join(str(p) for p in pages),
                "chunk_index": idx,
            },
        })
        # start the next chunk carrying the overlap tail
        cur = _overlap_tail(cur)
        cur_tokens = sum(_estimate_tokens(p[0]) for p in cur)

    for text, page in pieces:
        t = _estimate_tokens(text)
        if cur_tokens + t > _TARGET_TOKENS and cur:
            flush()
        cur.append((text, page))
        cur_tokens += t
    flush()


def build_pdf_chunks(extract, company_id: str, file_id: str) -> list[dict]:
    """Turn a PDF's prose into heading-aware, overlapping chunks with metadata.

    Walks the text blocks in order, remembering the current section heading and
    dropping noise (headers/footers/captions). Chunks never cross a heading, so
    each chunk belongs to exactly one section (clean citations + hierarchy). Each
    chunk carries a metadata card pointing HOME (file / page / section) plus a
    parent_id (the section) so hierarchical retrieval can switch on later.
    """
    chunks: list[dict] = []
    title = ""                              # document title (first pseudo-heading)
    frontmatter: list[tuple[str, int]] = []  # title + authors + affiliations
    frontmatter_tokens = 0
    in_frontmatter = True                   # True until the first REAL heading
    heading = ""                            # the heading currently open
    heading_page = 0                        # the page that heading appears on
    pieces: list[tuple[str, int]] = []      # content collected under `heading`

    def emit_frontmatter() -> None:
        nonlocal frontmatter
        _emit_frontmatter(chunks, title, frontmatter, company_id, file_id)
        frontmatter = []

    def close_current() -> None:
        """Close the just-collected block: front-matter (title/authors) or section."""
        nonlocal pieces, heading, heading_page, title
        nonlocal frontmatter, frontmatter_tokens, in_frontmatter
        if not heading and not pieces:
            return
        content_tokens = sum(_estimate_tokens(t) for t, _ in pieces)

        # While still in front matter AND this is not a real heading, it's the
        # title or an author block -> accumulate it. A REAL heading (ABSTRACT or
        # "1 Introduction") is what ENDS the front matter — authors always come
        # before the first real heading, so this reliably separates them.
        if in_frontmatter and not _is_real_heading(heading):
            if heading and not title:
                title = heading             # the first pseudo-heading is the title
            elif heading:
                frontmatter.append((heading, heading_page))  # an author name
            frontmatter.extend(pieces)      # its affiliation line(s)
            frontmatter_tokens += content_tokens + (_estimate_tokens(heading) if heading else 0)
            if frontmatter_tokens > _FRONTMATTER_CAP:   # runaway guard (no headings)
                emit_frontmatter()
                in_frontmatter = False
        else:
            if in_frontmatter:              # first real heading ends the front matter
                emit_frontmatter()
                in_frontmatter = False
            _emit_section_chunks(chunks, pieces, heading, heading_page,
                                 title, company_id, file_id)
        pieces = []
        heading = ""
        heading_page = 0

    for block in extract.text_blocks:
        if block.label in _PDF_NOISE_LABELS:
            continue
        if block.label == "section_header":
            close_current()                 # close the previous block cleanly
            heading = block.text
            heading_page = block.page
            continue
        # a content block (paragraph or bullet): split it if it's oversized,
        # then add its pieces to the current buffer.
        for piece in _split_oversize(block.text):
            pieces.append((piece, block.page))
    close_current()

    if in_frontmatter:                      # doc had no real heading at all
        emit_frontmatter()

    return chunks
