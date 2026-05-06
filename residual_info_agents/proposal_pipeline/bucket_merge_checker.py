from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MergeCandidate:
  left_bucket_id: str
  right_bucket_id: str
  reason: str


class BucketMergeChecker:
  """Placeholder merge checker for MVP.

  Routing records close rankings, but automatic merge/split is intentionally
  left conservative until bucket quality metrics are available.
  """

  def find_candidates(self) -> list[MergeCandidate]:
    return []
