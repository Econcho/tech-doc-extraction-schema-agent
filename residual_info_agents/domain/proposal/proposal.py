from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class ProposedAttribute:
  name: str
  description: str
  value_type: str = "string"
  required: bool = False


@dataclasses.dataclass
class ProposalDraft:
  proposal_id: str
  bucket_id: str
  proposal_type: str
  proposed_name: str
  definition: str
  motivation: str
  related_old_schema_name: str
  supporting_signal_ids: list[str]
  representative_examples: list[str]
  attributes: list[ProposedAttribute] = dataclasses.field(default_factory=list)
  confidence: float = 0.0
  risk_flags: list[str] = dataclasses.field(default_factory=list)
  created_at: str = ""


@dataclasses.dataclass
class ProposalCheckResult:
  proposal_id: str
  bucket_id: str
  passed: bool
  conflict_type: str = "none"
  conflicting_schema_names: list[str] = dataclasses.field(default_factory=list)
  reason: str = ""
  suggested_action: str = "accept"
