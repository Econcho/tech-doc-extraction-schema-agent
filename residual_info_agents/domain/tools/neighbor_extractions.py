from __future__ import annotations

import dataclasses

from langextract.core.data import CharInterval


@dataclasses.dataclass
class SimplifiedExtraction:
  """Compact extraction result used by residual triage tools."""

  extraction_class: str
  extraction_text: str
  char_interval: CharInterval
  attributes: dict | None = None


@dataclasses.dataclass
class NeighborExtractions:
  """Extraction results near one residual block."""

  resblock_id: int
  extraction: list[SimplifiedExtraction]
