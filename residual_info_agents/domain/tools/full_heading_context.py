from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class FullHeadingContext:
  """Original document content for a heading tree."""

  heading_tree: list[str]
  content: str
