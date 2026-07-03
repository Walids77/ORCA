"""ORCA ingestion doorman.

One entry point that looks at a file, decides its TYPE, and routes it to the
right specialist processor (excel / pdf / image).

Why detect by CONTENT and not just the file name:
- The extension (".xlsx") can lie — a file can be renamed, mislabeled, or
  corrupted. So we ALSO read the first few bytes ("magic bytes") that every file
  format starts with, and trust that when the two disagree.

Right now only the Excel specialist gets built; PDF and image are honest stubs
(they raise "not built yet") so the routing is complete and testable without
half-building things our data doesn't need yet.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# THE FOUR ANSWERS THE DOORMAN CAN GIVE
# =============================================================================
EXCEL = "excel"
PDF = "pdf"
IMAGE = "image"
UNKNOWN = "unknown"

# File extensions we recognise, grouped by type.
_EXCEL_EXTS = {".xlsx", ".xlsm", ".xls"}
_PDF_EXTS = {".pdf"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}

# "Magic bytes" — the fixed signature at the very start of each format.
# (kind, signature-bytes) pairs. Checked against the first bytes of the file.
_MAGIC_SIGNATURES: list[tuple[str, bytes]] = [
    (PDF, b"%PDF"),               # every PDF starts with %PDF
    (IMAGE, b"\x89PNG\r\n\x1a\n"),  # PNG
    (IMAGE, b"\xff\xd8\xff"),      # JPEG
    (IMAGE, b"GIF8"),              # GIF
    (IMAGE, b"BM"),                # BMP
    (IMAGE, b"II*\x00"),           # TIFF (little-endian)
    (IMAGE, b"MM\x00*"),           # TIFF (big-endian)
    # NOTE: .xlsx is a ZIP, and .xls is an OLE file — both handled specially below,
    # because a ZIP signature alone is not enough to say "this is Excel".
]

# A raised error the caller can catch and turn into a friendly message.
class UnsupportedFileTypeError(Exception):
    """The file is not a type ORCA can ingest."""


# =============================================================================
# TYPE DETECTION
# =============================================================================
def _sniff_content(path: Path) -> str:
    """Look INSIDE the file (first bytes / structure) and guess the type.

    Returns EXCEL / PDF / IMAGE / UNKNOWN based only on content, ignoring the name.
    """
    # Read the first 8 bytes — enough for every signature above.
    with open(path, "rb") as f:
        head = f.read(8)

    # Simple prefix signatures (PDF + images).
    for kind, sig in _MAGIC_SIGNATURES:
        if head.startswith(sig):
            return kind

    # .xls (old Excel) is an OLE compound file: starts with D0 CF 11 E0.
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return EXCEL

    # .xlsx is a ZIP (starts with "PK") — but so are .docx, .pptx, plain .zip.
    # To be sure it is Excel, peek inside: real .xlsx has an "xl/" folder.
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as zf:
                if any(name.startswith("xl/") for name in zf.namelist()):
                    return EXCEL
        except zipfile.BadZipFile:
            return UNKNOWN
        return UNKNOWN  # a ZIP, but not an Excel workbook

    return UNKNOWN


def _type_from_extension(path: Path) -> str:
    """Guess the type from the file name's extension alone."""
    ext = path.suffix.lower()
    if ext in _EXCEL_EXTS:
        return EXCEL
    if ext in _PDF_EXTS:
        return PDF
    if ext in _IMAGE_EXTS:
        return IMAGE
    return UNKNOWN


def detect_file_type(file_path: str | Path) -> str:
    """Decide what kind of file this is: EXCEL / PDF / IMAGE / UNKNOWN.

    Uses BOTH the extension and the real content. If they disagree, the content
    wins (and we log a warning) — because the bytes can't be faked by a rename.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    by_ext = _type_from_extension(path)
    by_content = _sniff_content(path)

    # Content is authoritative: every type we support (xlsx=ZIP, xls=OLE, pdf=%PDF,
    # png/jpg/...) has a mandatory signature. So if the content confirms a type we
    # trust it; if the content CANNOT confirm any type, the file is unknown even if
    # the name claims otherwise (a renamed/corrupt file must not sneak through).
    if by_content != UNKNOWN:
        if by_ext != UNKNOWN and by_ext != by_content:
            logger.warning(
                "Extension says %r but the file content is %r - trusting the content. (%s)",
                by_ext, by_content, path.name,
            )
        return by_content

    if by_ext != UNKNOWN:
        logger.warning(
            "Name claims %r but the file content does not confirm it - treating as unknown. (%s)",
            by_ext, path.name,
        )
    return UNKNOWN


# =============================================================================
# ROUTING — hand the file to the right specialist
# =============================================================================
def _excel_not_ready(path: Path):
    raise NotImplementedError("Excel processor is the next build step (stages 1-7).")


def _pdf_not_ready(path: Path):
    raise NotImplementedError("PDF processor is a stub — not built yet.")


def _image_not_ready(path: Path):
    raise NotImplementedError("Image processor is a stub — not built yet.")


# The dispatch table: file type → the specialist that handles it.
# As we build each processor we swap its stub here for the real function.
_HANDLERS = {
    EXCEL: _excel_not_ready,
    PDF: _pdf_not_ready,
    IMAGE: _image_not_ready,
}


def route(file_path: str | Path):
    """Detect the file type and send it to the matching specialist.

    Returns whatever the specialist returns. Raises UnsupportedFileTypeError for
    unknown types (the caller turns that into a friendly "can't read this" message).
    """
    path = Path(file_path)
    file_type = detect_file_type(path)

    if file_type == UNKNOWN:
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {path.name}. "
            f"ORCA accepts Excel, PDF, and image files."
        )

    handler = _HANDLERS[file_type]
    logger.info("Routing %s → %s processor", path.name, file_type)
    return handler(path)
