"""Data models for decoupled evaluation registries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RegistryEntry:
  """Represents one registered source document and its label file."""

  doc_id: str
  doc_type: str
  document_path: str
  label_path: str
  enabled: bool = True
  metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetRegistry:
  """Represents one independent evaluation subset registry file."""

  registry_name: str
  version: str
  domain: str
  schema_version: str
  entries: tuple[RegistryEntry, ...]
