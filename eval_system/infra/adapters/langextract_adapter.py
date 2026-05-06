"""Adapter for LangExtract-style prediction output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import EvalDocument, EvalExtraction


class LangExtractAdapter:
  """Converts LangExtract output files into internal evaluation documents."""

  def load(self, source: str, **kwargs: Any) -> list[EvalDocument]:
    """Load one LangExtract prediction file."""
    path = Path(source)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
      raise ValueError("LangExtract adapter expects a JSON array.")
    doc_id = kwargs.get("doc_id")
    if not doc_id:
      raise ValueError("LangExtract adapter requires doc_id in kwargs.")

    extractions = tuple(
        EvalExtraction(
            extraction_class=item["extraction_class"],
            extraction_text=item["extraction_text"],
            attributes=item.get("attributes") or {},
            alignment_status=item.get("alignment_status"),
        )
        for item in payload
    )
    return [
        EvalDocument(
            doc_id=doc_id,
            domain=kwargs.get("domain", ""),
            split=kwargs.get("split"),
            extractions=extractions,
            metadata={"source_path": str(path)},
        )
    ]
