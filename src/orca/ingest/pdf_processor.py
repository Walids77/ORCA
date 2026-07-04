"""ORCA PDF processor.

Turns a PDF into a clean, structured object — its tables and its text blocks,
each tagged with the page it came from — using **Docling** (IBM's open-source,
layout-aware document parser).

Why Docling instead of the old ORCA's approach:
- The old ORCA glued three libraries together (PyPDF2 for text, pdfplumber for
  tables, PyMuPDF for images) and then chunked text with a blind character-slicer.
  A plain text dump loses the page layout, so a price floats away from its product
  and a number away from its label.
- Docling runs an AI *layout model* (finds titles / paragraphs / tables) + a
  *table-structure model*, so a table stays a real grid and a heading stays a
  heading. That structure is what later stages need to send NUMBERS to SQL and
  PROSE to the vector store.

This file currently covers STAGE 1 of the PDF pipeline:
  1. EXTRACT — Docling → a `PdfExtract` (tables + text blocks + page numbers +
     the full markdown). Faithful capture only; no typing / no SQL-vs-prose
     decision yet (those are later stages, mirroring the Excel processor).

The output is a `PdfExtract`: a plain data object the later stages read from —
the same design as the Excel processor's `WorkbookExtract`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PdfProcessingError(Exception):
    """Raised when a PDF cannot be read."""


# =============================================================================
# THE SHAPE OF THE RESULT  (what the later stages will read)
# =============================================================================
@dataclass
class PdfTable:
    """One table Docling found on a page.

    Rows are kept as-extracted (text) for now — number typing + the decision of
    "is this a numeric table for SQL, or a key-value block for prose?" happen in a
    later stage, exactly like the Excel processor does it.
    """
    page: int                       # 1-based PDF page the table was found on
    columns: list[str]              # column headers as Docling read them
    rows: list[dict[str, Any]]      # each row: {column_name: cell_text}

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    @property
    def n_cols(self) -> int:
        return len(self.columns)


@dataclass
class PdfTextBlock:
    """One piece of non-table text Docling found, with its structural label.

    `label` is Docling's own tag for the block — e.g. 'section_header', 'text',
    'list_item', 'caption', 'page_header', 'page_footer'. The chunker uses it to
    keep headings, group paragraphs, and DROP noise like page headers/footers.
    """
    page: int                       # 1-based PDF page
    label: str                      # section_header / text / list_item / caption / ...
    text: str


@dataclass
class PdfExtract:
    """The whole PDF after stage 1."""
    file_path: str
    page_count: int
    tables: list[PdfTable] = field(default_factory=list)
    text_blocks: list[PdfTextBlock] = field(default_factory=list)
    markdown: str = ""              # full document as markdown (handy for chunking + debug)


# =============================================================================
# THE DOCLING CONVERTER  (loaded once, reused — the models are slow to load)
# =============================================================================
_converter = None  # module-level cache


def _get_converter():
    """Build the Docling converter once and reuse it.

    Creating a DocumentConverter loads the layout + table AI models into memory,
    which takes a few seconds — so we do it a single time and keep it.
    """
    global _converter
    if _converter is None:
        # Imported here (not at top) so importing this module stays cheap; the
        # heavy Docling import only happens when we actually process a PDF.
        from docling.document_converter import DocumentConverter
        logger.info("Loading Docling models (first call in this process)...")
        _converter = DocumentConverter()
    return _converter


# =============================================================================
# STAGE 1 - the main entry point
# =============================================================================
def _page_of(item: Any) -> int:
    """Read the 1-based page number Docling recorded for a text/table item."""
    prov = getattr(item, "prov", None)
    if prov:
        return prov[0].page_no
    return 0


def _table_to_rows(table: Any, doc: Any) -> tuple[list[str], list[dict[str, Any]]]:
    """Turn one Docling table into (columns, rows) using its dataframe export."""
    df = table.export_to_dataframe(doc)
    columns = [str(c) for c in df.columns]
    rows = [
        {col: ("" if v is None else str(v)).strip() for col, v in record.items()}
        for record in df.to_dict(orient="records")
    ]
    return columns, rows


def extract_pdf(pdf_path: str | Path, max_pages: int | None = None) -> PdfExtract:
    """Open a PDF with Docling and return its tables + text blocks (stage 1).

    max_pages: if given, only the first N pages are read (handy for peeking at a
    long file like the 37-page catalog without processing all of it).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    logger.info("Converting PDF with Docling: %s", path.name)
    try:
        if max_pages:
            # page_range is 1-based inclusive: read pages 1..max_pages only.
            # (max_num_pages is a hard ceiling that ERRORS on longer files, so we
            #  use page_range, which simply truncates to the range.)
            result = _get_converter().convert(str(path), page_range=(1, max_pages))
        else:
            result = _get_converter().convert(str(path))
    except Exception as e:  # Docling raises various types for unreadable files
        raise PdfProcessingError(f"Could not read PDF: {e}") from e

    doc = result.document

    # --- tables: keep each as a faithful grid, tagged with its page -----------
    tables: list[PdfTable] = []
    for t in doc.tables:
        try:
            columns, rows = _table_to_rows(t, doc)
        except Exception as e:
            logger.warning("Skipping a table that failed to export: %s", e)
            continue
        tables.append(PdfTable(page=_page_of(t), columns=columns, rows=rows))

    # --- text blocks: every non-table text item, with its label + page --------
    text_blocks: list[PdfTextBlock] = []
    for item in doc.texts:
        text = (item.text or "").strip()
        if not text:
            continue
        text_blocks.append(PdfTextBlock(
            page=_page_of(item),
            label=str(getattr(item, "label", "text")),
            text=text,
        ))

    # page_count: highest page number we saw (Docling doesn't expose it directly
    # on every version, so we infer it from the items' provenance).
    seen_pages = [b.page for b in text_blocks] + [t.page for t in tables]
    page_count = max(seen_pages) if seen_pages else 0

    extract = PdfExtract(
        file_path=str(path),
        page_count=page_count,
        tables=tables,
        text_blocks=text_blocks,
        markdown=doc.export_to_markdown(),
    )
    logger.info(
        "Extracted %s: %d page(s), %d table(s), %d text block(s)",
        path.name, page_count, len(tables), len(text_blocks),
    )
    return extract


# =============================================================================
# CONVENIENCE - run this file directly to inspect a PDF's extraction
#   python -m orca.ingest.pdf_processor "data/Salary Slip January 2019.pdf"
# =============================================================================
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print('Usage: python -m orca.ingest.pdf_processor "<path-to-pdf>"')
        raise SystemExit(1)

    ex = extract_pdf(sys.argv[1])
    print(f"\nFILE: {ex.file_path}")
    print(f"PAGES: {ex.page_count} | TABLES: {len(ex.tables)} | TEXT BLOCKS: {len(ex.text_blocks)}")

    for i, tbl in enumerate(ex.tables, 1):
        print(f"\n--- table {i} (page {tbl.page}, {tbl.n_rows}x{tbl.n_cols}) ---")
        print("columns:", tbl.columns)
        for r in tbl.rows[:8]:
            print(" ", r)

    print("\n--- text blocks (label · page) ---")
    for b in ex.text_blocks:
        print(f"[{b.label}] p{b.page}: {b.text[:90]}")
