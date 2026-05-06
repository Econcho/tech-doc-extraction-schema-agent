from __future__ import annotations

import dataclasses

from residual_info_agents.domain.runtime.heading_runtime_context import (
    HeadingRuntimeContext,
)
from residual_info_agents.domain.runtime.resblock_runtime_info import (
    ResBlockRuntimeInfo,
)


@dataclasses.dataclass
class TriageWorkingContext:
  """Runtime evidence visible to the triage agent."""

  resblocks: list[ResBlockRuntimeInfo]
  heading_contexts: list[HeadingRuntimeContext] = dataclasses.field(
      default_factory=list
  )
