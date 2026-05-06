from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class HeadingRuntimeContext:
  """Section-level context shared by residual blocks under a heading tree."""

  heading_tree: list[str]
  content: str
  source_tool_use_id: str
