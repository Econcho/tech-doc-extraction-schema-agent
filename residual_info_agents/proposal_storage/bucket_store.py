from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from residual_info_agents.domain.proposal.bucket import Bucket
from residual_info_agents.domain.proposal.bucket import BucketLineage
from residual_info_agents.domain.proposal.enums import BucketProposalType
from residual_info_agents.domain.proposal.enums import BucketStatus
from residual_info_agents.domain.proposal.signal import TriageSignal
from residual_info_agents.proposal_storage.jsonl_store import to_jsonable


def utc_now() -> str:
  return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class BucketStore:
  def __init__(self, path: str | Path):
    self.path = Path(path)

  def create_bucket(
      self,
      proposal_type: str,
      first_signal: TriageSignal | None = None,
  ) -> Bucket:
    now = utc_now()
    bucket = Bucket(
        bucket_id=f"bucket_{now.replace(':', '').replace('-', '')}_"
        f"{len(self.list_buckets()) + 1}",
        type=BucketProposalType(proposal_type),
        created_at=now,
        updated_at=now,
    )
    if first_signal is not None:
      bucket.member_signal_ids.append(first_signal.signal_id)
      self._refresh_support(bucket, [first_signal])
    self.save_bucket(bucket)
    return bucket

  def save_bucket(self, bucket: Bucket) -> None:
    buckets = {item.bucket_id: item for item in self.list_buckets()}
    buckets[bucket.bucket_id] = bucket
    self._write_buckets(list(buckets.values()))

  def append_signal(self, bucket_id: str, signal: TriageSignal) -> Bucket:
    bucket = self.get_bucket(bucket_id)
    if signal.signal_id not in bucket.member_signal_ids:
      bucket.member_signal_ids.append(signal.signal_id)
    bucket.support_signal_count = len(bucket.member_signal_ids)
    bucket.updated_at = utc_now()
    self.save_bucket(bucket)
    return bucket

  def refresh_support(
      self, bucket_id: str, signals: list[TriageSignal]
  ) -> Bucket:
    bucket = self.get_bucket(bucket_id)
    self._refresh_support(bucket, signals)
    bucket.updated_at = utc_now()
    self.save_bucket(bucket)
    return bucket

  def update_status(self, bucket_id: str, status: BucketStatus | str) -> Bucket:
    bucket = self.get_bucket(bucket_id)
    bucket.status = BucketStatus(status)
    bucket.updated_at = utc_now()
    self.save_bucket(bucket)
    return bucket

  def get_bucket(self, bucket_id: str) -> Bucket:
    for bucket in self.list_buckets():
      if bucket.bucket_id == bucket_id:
        return bucket
    raise ValueError(f"Unknown bucket id: {bucket_id}")

  def list_buckets(self) -> list[Bucket]:
    if not self.path.exists():
      return []
    data = json.loads(self.path.read_text(encoding="utf-8") or "[]")
    return [self._bucket_from_dict(item) for item in data]

  def _write_buckets(self, buckets: list[Bucket]) -> None:
    self.path.parent.mkdir(parents=True, exist_ok=True)
    self.path.write_text(
        json.dumps(to_jsonable(buckets), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

  @staticmethod
  def _refresh_support(bucket: Bucket, signals: list[TriageSignal]) -> None:
    member_ids = set(bucket.member_signal_ids)
    bucket.support_signal_count = len(member_ids)
    bucket.support_doc_count = len(
        {signal.doc_ref for signal in signals if signal.signal_id in member_ids}
    )

  @staticmethod
  def _bucket_from_dict(data: dict[str, Any]) -> Bucket:
    lineage_data = data.get("lineage")
    lineage = BucketLineage(**lineage_data) if isinstance(lineage_data, dict) else None
    return Bucket(
        bucket_id=str(data["bucket_id"]),
        type=BucketProposalType(data["type"]),
        status=BucketStatus(data.get("status", BucketStatus.INCUBATING.value)),
        version=int(data.get("version", 1)),
        member_signal_ids=list(data.get("member_signal_ids", [])),
        support_doc_count=int(data.get("support_doc_count", 0)),
        support_signal_count=int(data.get("support_signal_count", 0)),
        lineage=lineage,
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
    )
