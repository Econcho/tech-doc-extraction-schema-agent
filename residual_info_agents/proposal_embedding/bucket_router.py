from __future__ import annotations

import dataclasses

from residual_info_agents.domain.proposal.signal import TriageSignal
from residual_info_agents.proposal_embedding.bucket_ranker import BucketRanker
from residual_info_agents.proposal_embedding.bucket_ranker import BucketRankResult
from residual_info_agents.proposal_embedding.embedding_client import EmbeddingClient
from residual_info_agents.proposal_embedding.vector_store import VectorHit
from residual_info_agents.proposal_embedding.vector_store import VectorStore
from residual_info_agents.proposal_storage.bucket_store import BucketStore


@dataclasses.dataclass
class RouteDecision:
  bucket_id: str
  created_new_bucket: bool
  score: float | None
  route_reason: str
  rankings: list[BucketRankResult]


class BucketRouter:
  def __init__(
      self,
      embedding_client: EmbeddingClient,
      vector_store: VectorStore,
      bucket_store: BucketStore,
      ranker: BucketRanker,
      top_k: int = 20,
      route_threshold: float = 0.6,
  ):
    self.embedding_client = embedding_client
    self.vector_store = vector_store
    self.bucket_store = bucket_store
    self.ranker = ranker
    self.top_k = top_k
    self.route_threshold = route_threshold

  def route(self, signal: TriageSignal) -> RouteDecision:
    source_vector, reason_vector = self.embedding_client.embed_texts([
        signal.source_embedding_text,
        signal.reason_embedding_text,
    ])
    hits = self._combine_hits(
        self.vector_store.search(source_vector, self.top_k, "source_index"),
        self.vector_store.search(reason_vector, self.top_k, "reason_index"),
    )
    rankings = self.ranker.rank(hits)
    if rankings and rankings[0].score >= self.route_threshold:
      return RouteDecision(
          bucket_id=rankings[0].bucket_id,
          created_new_bucket=False,
          score=rankings[0].score,
          route_reason="matched_existing_bucket",
          rankings=rankings,
      )

    bucket = self.bucket_store.create_bucket(signal.conclusion, signal)
    return RouteDecision(
        bucket_id=bucket.bucket_id,
        created_new_bucket=True,
        score=rankings[0].score if rankings else None,
        route_reason="created_new_bucket",
        rankings=rankings,
    )

  def index_signal(self, signal: TriageSignal, bucket_id: str) -> None:
    source_vector, reason_vector = self.embedding_client.embed_texts([
        signal.source_embedding_text,
        signal.reason_embedding_text,
    ])
    self.vector_store.add(
        signal.signal_id, bucket_id, source_vector, "source_index"
    )
    self.vector_store.add(
        signal.signal_id, bucket_id, reason_vector, "reason_index"
    )

  @staticmethod
  def _combine_hits(
      source_hits: list[VectorHit],
      reason_hits: list[VectorHit],
  ) -> list[VectorHit]:
    scores: dict[tuple[str, str], VectorHit] = {}
    for hits in (source_hits, reason_hits):
      for hit in hits:
        key = (hit.signal_id, hit.bucket_id)
        rrf_score = 1.0 / (60 + hit.rank)
        if key not in scores:
          scores[key] = VectorHit(
              signal_id=hit.signal_id,
              bucket_id=hit.bucket_id,
              similarity=rrf_score,
              rank=hit.rank,
              index_name="combined",
          )
        else:
          scores[key].similarity += rrf_score
          scores[key].rank = min(scores[key].rank, hit.rank)
    combined = list(scores.values())
    combined.sort(key=lambda hit: hit.similarity, reverse=True)
    for index, hit in enumerate(combined, start=1):
      hit.rank = index
    return combined
