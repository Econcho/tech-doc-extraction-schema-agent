"""Generic JSON and JSONL adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import EvalDocument, EvalExtraction


class JsonAdapter:
  """Loads JSON or JSONL documents into internal evaluation models."""

  def load(self, source: str, **kwargs: Any) -> list[EvalDocument]:
    """Load documents from JSON or JSONL files."""
    path = Path(source)
    if path.suffix == ".jsonl":
      rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
      rows = json.loads(path.read_text(encoding="utf-8"))
      if isinstance(rows, dict):
        rows = [rows]
    return [self._to_document(row, **kwargs) for row in rows]

  def _to_document(self, row: dict[str, Any], **kwargs: Any) -> EvalDocument:
    """Convert one raw row into an internal document."""
    doc_id = row.get("doc_id") or kwargs.get("doc_id")
    if not doc_id:
      raise ValueError("JSON adapter requires doc_id in the payload or kwargs.")
    extractions = tuple(
        EvalExtraction(
            extraction_class=item["extraction_class"],
            extraction_text=item["extraction_text"],
            attributes=item.get("attributes") or {},
            alignment_status=item.get("alignment_status"),
        )
        for item in row.get("extractions", row.get("items", []))
    )
    return EvalDocument(
        doc_id=doc_id,
        domain=row.get("domain", kwargs.get("domain", "")),
        split=row.get("split", kwargs.get("split")),
        extractions=extractions,
        text=row.get("text"),
        metadata=row.get("metadata", {}),
    )
