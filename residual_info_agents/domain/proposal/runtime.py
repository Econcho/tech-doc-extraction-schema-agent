from __future__ import annotations

import dataclasses

from residual_info_agents.domain.proposal.bucket import Bucket
from residual_info_agents.domain.proposal.signal import SignalInfoRuntimeBlock
from residual_info_agents.domain.tools.tool_result import ToolResult


@dataclasses.dataclass
class ProposalWorkingContext:
  bucket_id: str
  bucket_type: str
  schema_description: str
  signals: list[SignalInfoRuntimeBlock]
  bucket_metadata: Bucket
  tool_results: list[ToolResult] = dataclasses.field(default_factory=list)
  turn_count: int = 0


@dataclasses.dataclass
class ProposalLoopState:
  context: ProposalWorkingContext
  turn_count: int
  transition_reason: str
