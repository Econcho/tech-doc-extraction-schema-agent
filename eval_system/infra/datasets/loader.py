"""Registry-driven dataset loading logic."""

from __future__ import annotations

import json
from pathlib import Path

from ..core.models import EvalDocument, EvalExtraction
from ..registry.service import RegistryService


class DatasetLoader:
  """Loads gold documents from one registry file."""

  def __init__(self) -> None:
    """Initialize the registry-backed dataset loader."""
    self.registry_service = RegistryService()

  def load_registry(self, registry_path: str | Path) -> tuple[dict[str, EvalDocument], dict]:
    """Load gold documents from one decoupled registry file."""
    registry = self.registry_service.load(registry_path)
    docs: dict[str, EvalDocument] = {}

    for entry in self.registry_service.list_entries(registry_path):
      document_path, label_path = self.registry_service.resolve_entry_paths(
          registry_path,
          entry,
      )
      payload = json.loads(label_path.read_text(encoding="utf-8"))
      extractions = tuple(
          EvalExtraction(
              extraction_class=item["extraction_class"],
              extraction_text=item["extraction_text"],
              attributes=item.get("attributes") or {},
          )
          for item in payload
      )
      docs[entry.doc_id] = EvalDocument(
          doc_id=entry.doc_id,
          domain=registry.domain,
          split=registry.registry_name,
          extractions=extractions,
          text=document_path.read_text(encoding="utf-8") if document_path.exists() else None,
          metadata={
              "gold_path": str(label_path),
              "doc_path": str(document_path),
              "doc_type": entry.doc_type,
              "registry_name": registry.registry_name,
              **entry.metadata,
          },
      )

    return docs, {
        "dataset_name": registry.registry_name,
        "version": registry.version,
        "domain": registry.domain,
        "schema_version": registry.schema_version,
        "label_policy_version": "registry_label_files",
        "split": registry.registry_name,
        "doc_count": len(docs),
        "registry_path": str(Path(registry_path)),
    }
