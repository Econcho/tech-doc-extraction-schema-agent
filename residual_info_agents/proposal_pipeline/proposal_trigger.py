from __future__ import annotations

from typing import Any

from residual_info_agents.proposal_embedding.bucket_monitor import BucketMonitor
from residual_info_agents.proposal_storage.bucket_store import BucketStore


def get_allow_proposal_buckets(config: dict[str, Any]) -> list[str]:
  storage = config.get("storage", {})
  allow = config.get("allow_proposal", {})
  monitor = BucketMonitor(
      BucketStore(storage["bucket_store_path"]),
      min_support_doc_count=int(allow.get("min_support_doc_count", 2)),
      min_support_signal_count=int(allow.get("min_support_signal_count", 5)),
  )
  return [bucket.bucket_id for bucket in monitor.get_allow_proposal_buckets()]
