from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ToolResult:
  """Serialized result for one tool invocation."""

  tool_use_id: str
  result: str | None = None
