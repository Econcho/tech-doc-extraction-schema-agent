from __future__ import annotations

from residual_info_agents.domain.proposal.enums import BucketStatus
from residual_info_agents.domain.proposal.bucket import Bucket
from residual_info_agents.proposal_storage.bucket_store import BucketStore


class BucketMonitor:
  def __init__(
      self,
      bucket_store: BucketStore,
      min_support_doc_count: int = 2,
      min_support_signal_count: int = 5,
  ):
    self.bucket_store = bucket_store
    self.min_support_doc_count = min_support_doc_count
    self.min_support_signal_count = min_support_signal_count

  def allow_proposal(self, bucket: Bucket) -> bool:
    return (
        bucket.support_doc_count >= self.min_support_doc_count
        and bucket.support_signal_count >= self.min_support_signal_count
        and bucket.status
        in {BucketStatus.INCUBATING, BucketStatus.STABLE}
    )

  def get_allow_proposal_buckets(self) -> list[Bucket]:
    buckets = []
    for bucket in self.bucket_store.list_buckets():
      if self.allow_proposal(bucket):
        buckets.append(self.bucket_store.update_status(bucket.bucket_id, "stable"))
    return buckets
