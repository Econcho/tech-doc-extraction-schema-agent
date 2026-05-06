from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from residual_info_agents.domain.proposal.enums import SignalBucketMappingStatus
from residual_info_agents.domain.proposal.mapping import SignalBucketMapping
from residual_info_agents.domain.proposal.signal import TriageSignal
from residual_info_agents.proposal_embedding.bucket_ranker import BucketRanker
from residual_info_agents.proposal_embedding.bucket_router import BucketRouter
from residual_info_agents.proposal_embedding.embedding_client import EmbeddingClient
from residual_info_agents.proposal_embedding.vector_store import VectorStore
from residual_info_agents.proposal_storage.bucket_store import BucketStore
from residual_info_agents.proposal_storage.mapping_store import MappingStore
from residual_info_agents.proposal_storage.signal_store import SignalStore


def utc_now() -> str:
  return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class SignalIngestion:
  def __init__(self, config: dict[str, Any]):
    storage = config.get("storage", {})
    embedding = config.get("embedding", {})
    routing = config.get("bucket_routing", {})
    self.signal_store = SignalStore(storage["signal_store_path"])
    self.bucket_store = BucketStore(storage["bucket_store_path"])
    self.mapping_store = MappingStore(storage["mapping_store_path"])
    self.embedding_client = EmbeddingClient(**embedding)
    self.vector_store = VectorStore.from_config(embedding)
    self.router = BucketRouter(
        embedding_client=self.embedding_client,
        vector_store=self.vector_store,
        bucket_store=self.bucket_store,
        ranker=BucketRanker(
            tau_high=float(routing.get("tau_high", 0.75)),
            tau_low=float(routing.get("tau_low", 0.45)),
            weak_alpha=float(routing.get("weak_alpha", 0.3)),
        ),
        top_k=int(embedding.get("top_k", 20)),
        route_threshold=float(routing.get("route_threshold", 0.6)),
    )

  def ingest(self, signals: list[TriageSignal]) -> list[SignalBucketMapping]:
    mappings = []
    for signal in signals:
      self.signal_store.append_signal(signal)
      decision = self.router.route(signal)
      if not decision.created_new_bucket:
        self.bucket_store.append_signal(decision.bucket_id, signal)
      self.router.index_signal(signal, decision.bucket_id)
      self.bucket_store.refresh_support(
          decision.bucket_id, self.signal_store.list_signals()
      )
      mapping = SignalBucketMapping(
          signal_id=signal.signal_id,
          bucket_id=decision.bucket_id,
          status=SignalBucketMappingStatus.ACTIVE,
          assigned_at=utc_now(),
          score=decision.score,
          route_reason=decision.route_reason,
      )
      self.mapping_store.append_mapping(mapping)
      mappings.append(mapping)
    return mappings


def load_config(path: str | Path) -> dict[str, Any]:
  import yaml  # pylint: disable=import-outside-toplevel

  return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
