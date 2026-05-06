from __future__ import annotations

import dataclasses
import math

from residual_info_agents.proposal_embedding.vector_store import VectorHit


@dataclasses.dataclass
class BucketRankResult:
  bucket_id: str
  score: float
  support_hit_count: int
  high_support_count: int
  low_penalty_count: int
  member_hit_ids: list[str]


class BucketRanker:
  def __init__(
      self,
      tau_high: float = 0.75,
      tau_low: float = 0.45,
      weak_alpha: float = 0.3,
      epsilon: float = 1e-9,
  ):
    self.tau_high = tau_high
    self.tau_low = tau_low
    self.weak_alpha = weak_alpha
    self.epsilon = epsilon

  def rank(self, hits: list[VectorHit]) -> list[BucketRankResult]:
    buckets: dict[str, list[VectorHit]] = {}
    for hit in hits:
      buckets.setdefault(hit.bucket_id, []).append(hit)

    results = []
    for bucket_id, bucket_hits in buckets.items():
      weights = [self._weight(hit.similarity) for hit in bucket_hits]
      positive_weights = [weight for weight in weights if weight > 0]
      numerator = sum(positive_weights) ** 2
      denominator = (
          sum(weight * weight for weight in positive_weights) + self.epsilon
      )
      n_eff = numerator / denominator if positive_weights else 0.0
      score = math.log1p(n_eff) * sum(weights)
      results.append(
          BucketRankResult(
              bucket_id=bucket_id,
              score=score,
              support_hit_count=len(bucket_hits),
              high_support_count=sum(
                  1 for hit in bucket_hits if hit.similarity >= self.tau_high
              ),
              low_penalty_count=sum(
                  1 for hit in bucket_hits if hit.similarity <= self.tau_low
              ),
              member_hit_ids=[hit.signal_id for hit in bucket_hits],
          )
      )
    results.sort(key=lambda result: result.score, reverse=True)
    return results

  def _weight(self, similarity: float) -> float:
    if similarity >= self.tau_high:
      return (similarity - self.tau_high) / (1 - self.tau_high)
    if similarity <= self.tau_low:
      return -((self.tau_low - similarity) / self.tau_low)
    return self.weak_alpha * (
        (similarity - self.tau_low) / (self.tau_high - self.tau_low)
    )
