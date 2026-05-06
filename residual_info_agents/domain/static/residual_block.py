from __future__ import annotations

import dataclasses

from langextract.core.data import CharInterval


@dataclasses.dataclass
class ResidualBlock:
  """One cleaned residual text segment persisted as static input."""

  text: str
  block_id: int | None = None
  char_interval: CharInterval | None = None
  heading_tree: list[str] = dataclasses.field(default_factory=list)
