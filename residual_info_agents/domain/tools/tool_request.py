from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass
class ToolRequest:
  """Agent request to invoke one registered tool."""

  tool_use_id: str
  tool_name: str
  args: dict[str, Any]
