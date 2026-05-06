from __future__ import annotations

from pathlib import Path
from typing import Any

from residual_info_agents.domain.proposal.proposal import ProposalCheckResult
from residual_info_agents.domain.proposal.proposal import ProposalDraft
from residual_info_agents.domain.proposal.proposal import ProposedAttribute
from residual_info_agents.proposal_storage.jsonl_store import append_jsonl
from residual_info_agents.proposal_storage.jsonl_store import read_jsonl


class ProposalStore:
  def __init__(
      self,
      proposal_path: str | Path,
      check_path: str | Path,
  ):
    self.proposal_path = Path(proposal_path)
    self.check_path = Path(check_path)

  def save_proposal_draft(self, proposal: ProposalDraft) -> None:
    append_jsonl(self.proposal_path, proposal)

  def save_proposal_check(self, check: ProposalCheckResult) -> None:
    append_jsonl(self.check_path, check)

  def list_proposals_by_bucket(self, bucket_id: str) -> list[ProposalDraft]:
    return [
        self._proposal_from_dict(row)
        for row in read_jsonl(self.proposal_path)
        if row.get("bucket_id") == bucket_id
    ]

  @staticmethod
  def _proposal_from_dict(data: dict[str, Any]) -> ProposalDraft:
    return ProposalDraft(
        proposal_id=str(data["proposal_id"]),
        bucket_id=str(data["bucket_id"]),
        proposal_type=str(data["proposal_type"]),
        proposed_name=str(data["proposed_name"]),
        definition=str(data["definition"]),
        motivation=str(data["motivation"]),
        related_old_schema_name=str(data.get("related_old_schema_name", "")),
        supporting_signal_ids=list(data.get("supporting_signal_ids", [])),
        representative_examples=list(data.get("representative_examples", [])),
        attributes=[
            ProposedAttribute(**item)
            for item in data.get("attributes", [])
            if isinstance(item, dict)
        ],
        confidence=float(data.get("confidence", 0.0)),
        risk_flags=list(data.get("risk_flags", [])),
        created_at=str(data.get("created_at", "")),
    )
