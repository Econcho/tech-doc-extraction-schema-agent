"""Registry file loading logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import DatasetRegistry, RegistryEntry


class RegistryLoader:
  """Loads one registry JSON file into typed registry objects."""

  def load(self, registry_path: str | Path) -> DatasetRegistry:
    """Load a registry file and resolve it into immutable model objects."""
    path = Path(registry_path)
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    entries = tuple(
        RegistryEntry(
            doc_id=item["doc_id"],
            doc_type=item["doc_type"],
            document_path=item["document_path"],
            label_path=item["label_path"],
            enabled=item.get("enabled", True),
            metadata=item.get("metadata") or {},
        )
        for item in payload.get("entries", [])
    )
    return DatasetRegistry(
        registry_name=payload["registry_name"],
        version=payload["version"],
        domain=payload["domain"],
        schema_version=payload["schema_version"],
        entries=entries,
    )
