"""High-level services for working with decoupled registry files."""

from __future__ import annotations

from pathlib import Path

from .loader import RegistryLoader
from .models import DatasetRegistry, RegistryEntry


class RegistryService:
  """Provides a stable interface for evaluation code to consume registries."""

  def __init__(self) -> None:
    """Initialize the service with the default registry loader."""
    self.loader = RegistryLoader()

  def load(self, registry_path: str | Path) -> DatasetRegistry:
    """Load one registry file from disk."""
    return self.loader.load(registry_path)

  def list_entries(
      self,
      registry_path: str | Path,
      *,
      enabled_only: bool = True,
  ) -> tuple[RegistryEntry, ...]:
    """Return registered entries from one registry file."""
    registry = self.load(registry_path)
    if not enabled_only:
      return registry.entries
    return tuple(entry for entry in registry.entries if entry.enabled)

  def resolve_entry_paths(
      self,
      registry_path: str | Path,
      entry: RegistryEntry,
  ) -> tuple[Path, Path]:
    """Resolve entry-relative document and label paths to absolute filesystem paths."""
    base_dir = Path(registry_path).resolve().parent
    return base_dir / entry.document_path, base_dir / entry.label_path
