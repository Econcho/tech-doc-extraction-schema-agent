from __future__ import annotations

import dataclasses
import enum

from residual_info_agents.domain.tools.tool_result import ToolResult


class ResBlockState(str, enum.Enum):
  """Runtime state for one residual block in the triage loop."""

  PENDING = "pending"
  NEED_NEIGHBOR_CONTEXT = "need_neighbor_context"
  NEED_NEIGHBOR_EXTRACTION_RESULT = "need_neighbor_extraction_result"
  NEED_SECTION_CONTEXT = "need_section_context"


@dataclasses.dataclass
class ResBlockRuntimeInfo:
  """Runtime state for a residual block during triage."""

  block_id: str
  text: str
  heading_tree: list[str] = dataclasses.field(default_factory=list)
  tool_results: list[ToolResult] = dataclasses.field(default_factory=list)
  tool_budget_left: int = 3
