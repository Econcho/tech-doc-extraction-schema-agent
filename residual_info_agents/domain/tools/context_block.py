from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ContextBlock:
  """Neighbor text context for one residual block."""

  resblock_id: int
  resblock_text: str
  previous_neighbor_text: str
  next_neighbor_text: str
