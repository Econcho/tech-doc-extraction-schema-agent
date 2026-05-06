from __future__ import annotations

import dataclasses

from residual_info_agents.domain.proposal.enums import BucketProposalType
from residual_info_agents.domain.proposal.enums import BucketStatus


@dataclasses.dataclass
class BucketLineage:
  parent_bucket_ids: list[str] = dataclasses.field(default_factory=list)
  child_bucket_ids: list[str] = dataclasses.field(default_factory=list)
  merge_from: list[str] = dataclasses.field(default_factory=list)
  split_from: str | None = None
  operation_reason: str = ""


@dataclasses.dataclass
class Bucket:
  bucket_id: str
  type: BucketProposalType
  status: BucketStatus = BucketStatus.INCUBATING
  version: int = 1
  member_signal_ids: list[str] = dataclasses.field(default_factory=list)
  support_doc_count: int = 0
  support_signal_count: int = 0
  lineage: BucketLineage | None = None
  created_at: str = ""
  updated_at: str = ""
