from __future__ import annotations

import dataclasses
import enum

from residual_info_agents.domain.runtime.working_context import WorkingContext


class TransitionReason(str, enum.Enum):
  """Reason why the triage loop transitioned or stopped."""

  NO_ACTIVE_BLOCK = "no_active_block"


@dataclasses.dataclass
class LoopState:
  """Runtime state for the full triage loop."""

  context: WorkingContext
  turn_count: int
  transition_reason: TransitionReason
