"""Helpers for discovering document-label pairs and writing registry files."""

from __future__ import annotations

import json
from pathlib import Path


class FileSystemRegistryBuilder:
  """Builds registry payloads from a generic docs-plus-labels directory layout."""

  def discover_entries(
      self,
      dataset_root: str | Path,
      *,
      docs_dir: str = "docs",
      labels_dir: str = "labels",
      document_filename: str = "README.md",
      preferred_label_names: tuple[str, ...] = (
          "label_v2_normalized.json",
          "label_v2.json",
      ),
  ) -> list[dict[str, object]]:
    """Discover registered entries from a docs and labels directory tree."""
    root = Path(dataset_root)
    labels_root = root / labels_dir
    docs_root = root / docs_dir
    entries: list[dict[str, object]] = []

    for label_path in self._collect_preferred_label_paths(
        labels_root,
        preferred_label_names,
    ):
      relative_label = label_path.relative_to(labels_root)
      doc_id = relative_label.parent.name
      document_matches = sorted(docs_root.rglob(f"{doc_id}/{document_filename}"))
      if len(document_matches) != 1:
        continue
      document_path = document_matches[0]
      doc_type_parts = list(relative_label.parent.parts[:-1])
      entries.append(
          {
              "doc_id": doc_id,
              "doc_type": "/".join(doc_type_parts),
              "document_path": document_path.relative_to(root).as_posix(),
              "label_path": label_path.relative_to(root).as_posix(),
              "enabled": True,
              "metadata": {
                  "label_filename": label_path.name,
                  "document_filename": document_filename,
              },
          }
      )
    return entries

  def _collect_preferred_label_paths(
      self,
      labels_root: Path,
      preferred_label_names: tuple[str, ...],
  ) -> list[Path]:
    """Choose one preferred label file for each labeled document directory."""
    preferred_paths: dict[Path, Path] = {}
    for candidate in sorted(labels_root.rglob("*.json")):
      parent_dir = candidate.parent
      current = preferred_paths.get(parent_dir)
      if candidate.name not in preferred_label_names:
        continue
      if current is None:
        preferred_paths[parent_dir] = candidate
        continue
      if preferred_label_names.index(candidate.name) < preferred_label_names.index(current.name):
        preferred_paths[parent_dir] = candidate
    return sorted(preferred_paths.values())

  def build_registry_payload(
      self,
      dataset_root: str | Path,
      *,
      registry_name: str,
      version: str = "v1",
      domain: str,
      schema_version: str,
      docs_dir: str = "docs",
      labels_dir: str = "labels",
      document_filename: str = "README.md",
      preferred_label_names: tuple[str, ...] = (
          "label_v2_normalized.json",
          "label_v2.json",
      ),
  ) -> dict[str, object]:
    """Build the full JSON payload for one registry file."""
    return {
        "registry_name": registry_name,
        "version": version,
        "domain": domain,
        "schema_version": schema_version,
        "entries": self.discover_entries(
            dataset_root,
            docs_dir=docs_dir,
            labels_dir=labels_dir,
            document_filename=document_filename,
            preferred_label_names=preferred_label_names,
        ),
    }

  def write_registry(
      self,
      dataset_root: str | Path,
      registry_path: str | Path,
      *,
      registry_name: str,
      version: str = "v1",
      domain: str,
      schema_version: str,
      docs_dir: str = "docs",
      labels_dir: str = "labels",
      document_filename: str = "README.md",
      preferred_label_names: tuple[str, ...] = (
          "label_v2_normalized.json",
          "label_v2.json",
      ),
  ) -> Path:
    """Write a discovered registry payload to a JSON file."""
    path = Path(registry_path)
    payload = self.build_registry_payload(
        dataset_root,
        registry_name=registry_name,
        version=version,
        domain=domain,
        schema_version=schema_version,
        docs_dir=docs_dir,
        labels_dir=labels_dir,
        document_filename=document_filename,
        preferred_label_names=preferred_label_names,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
