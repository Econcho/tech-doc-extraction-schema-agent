from __future__ import annotations

from pathlib import Path
from typing import Any

from residual_info_agents.domain.proposal.enums import SignalBucketMappingStatus
from residual_info_agents.domain.proposal.mapping import SignalBucketMapping
from residual_info_agents.proposal_storage.jsonl_store import append_jsonl
from residual_info_agents.proposal_storage.jsonl_store import read_jsonl


class MappingStore:
  def __init__(self, path: str | Path):
    self.path = Path(path)

  def append_mapping(self, mapping: SignalBucketMapping) -> None:
    append_jsonl(self.path, mapping)

  def get_mapping_by_signal(self, signal_id: str) -> SignalBucketMapping | None:
    for mapping in reversed(self.list_mappings()):
      if mapping.signal_id == signal_id:
        return mapping
    return None

  def list_mappings_by_bucket(self, bucket_id: str) -> list[SignalBucketMapping]:
    return [
        mapping for mapping in self.list_mappings()
        if mapping.bucket_id == bucket_id
    ]

  def list_mappings(self) -> list[SignalBucketMapping]:
    return [self._mapping_from_dict(row) for row in read_jsonl(self.path)]

  @staticmethod
  def _mapping_from_dict(data: dict[str, Any]) -> SignalBucketMapping:
    return SignalBucketMapping(
        signal_id=str(data["signal_id"]),
        bucket_id=str(data["bucket_id"]),
        status=SignalBucketMappingStatus(data["status"]),
        assigned_at=str(data["assigned_at"]),
        score=data.get("score"),
        route_reason=data.get("route_reason"),
    )
