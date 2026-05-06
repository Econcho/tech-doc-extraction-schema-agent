from __future__ import annotations

import dataclasses

from residual_info_agents.domain.proposal.enums import SignalBucketMappingStatus


@dataclasses.dataclass
class SignalBucketMapping:
  signal_id: str
  bucket_id: str
  status: SignalBucketMappingStatus
  assigned_at: str
  score: float | None = None
  route_reason: str | None = None
