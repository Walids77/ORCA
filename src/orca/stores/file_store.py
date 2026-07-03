"""ORCA file store — keeps the raw uploaded file + a manifest.

Why keep the original file at all:
  - it's the source of truth we can re-process or let a user re-download,
  - its content hash lets us SKIP work when an identical file is re-uploaded,
  - the manifest is the "metadata registry" row for this upload (what sheets,
    how many rows, when) that ties the SQL + vector data back to one file.

Local folders now; the exact same interface moves to S3 later (one bucket,
keyed by company_id/file_id) without changing the callers.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import shutil
from pathlib import Path

from orca.ingest.excel_processor import WorkbookExtract

logger = logging.getLogger(__name__)


def file_hash(path: str | Path) -> str:
    """SHA-256 of the file's bytes — identical files share a hash."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class FileStore:
    """Stores raw files + manifests under a root folder (local stand-in for S3)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, company_id: str, file_id: str) -> Path:
        return self.root / company_id / file_id

    def existing_hash(self, company_id: str, file_id: str) -> str | None:
        """The stored file's hash from a previous upload, or None if new."""
        manifest = self._dir(company_id, file_id) / "manifest.json"
        if manifest.exists():
            return json.loads(manifest.read_text(encoding="utf-8")).get("file_hash")
        return None

    def store(self, company_id: str, file_id: str, source_path: str | Path,
              extract: WorkbookExtract) -> dict:
        """Copy the raw file in and write a manifest. Returns the manifest dict."""
        source_path = Path(source_path)
        dest_dir = self._dir(company_id, file_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_file = dest_dir / source_path.name
        shutil.copy2(source_path, dest_file)

        manifest = {
            "company_id": company_id,
            "file_id": file_id,
            "original_name": source_path.name,
            "stored_path": str(dest_file),
            "file_hash": file_hash(source_path),
            "size_bytes": source_path.stat().st_size,
            "ingested_at": _dt.datetime.now().isoformat(),
            "sheets": [
                {
                    "name": s.sheet_name,
                    "rows": s.n_rows,
                    "total_rows": len(s.aggregate_rows),
                    "columns": s.columns,
                    "side_blocks": len(s.aux_blocks),
                }
                for s in extract.sheets
            ],
        }
        (dest_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Stored raw file + manifest for %s/%s", company_id, file_id)
        return manifest
