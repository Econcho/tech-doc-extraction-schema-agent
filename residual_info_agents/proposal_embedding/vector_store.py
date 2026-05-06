from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass
class VectorHit:
  signal_id: str
  bucket_id: str
  similarity: float
  rank: int
  index_name: str


class VectorStore:
  """Milvus-backed vector store for proposal bucket routing."""

  def __init__(
      self,
      uri: str = "http://localhost:19530",
      token: str | None = None,
      database: str | None = None,
      source_collection: str = "proposal_source_vectors",
      reason_collection: str = "proposal_reason_vectors",
      dimension: int = 256,
      metric_type: str = "COSINE",
      vector_field_name: str = "vector",
      primary_field_name: str = "id",
  ):
    try:
      from pymilvus import MilvusClient  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
      raise ImportError(
          "VectorStore requires pymilvus. Install it with "
          '`pip install "pymilvus>=2.4.0"`.'
      ) from exc

    kwargs: dict[str, Any] = {"uri": uri}
    if token:
      kwargs["token"] = token
    if database:
      kwargs["db_name"] = database

    self.client = MilvusClient(**kwargs)
    self.collections = {
        "source_index": source_collection,
        "reason_index": reason_collection,
    }
    self.dimension = dimension
    self.metric_type = metric_type
    self.vector_field_name = vector_field_name
    self.primary_field_name = primary_field_name
    self._ensure_collections()

  @classmethod
  def from_config(cls, config: dict[str, Any]) -> VectorStore:
    milvus_config = config.get("milvus", {})
    return cls(
        uri=str(milvus_config.get("uri", "http://localhost:19530")),
        token=milvus_config.get("token"),
        database=milvus_config.get("database"),
        source_collection=str(
            milvus_config.get("source_collection", "proposal_source_vectors")
        ),
        reason_collection=str(
            milvus_config.get("reason_collection", "proposal_reason_vectors")
        ),
        dimension=int(config.get("dimension", 256)),
        metric_type=str(milvus_config.get("metric_type", "COSINE")),
        vector_field_name=str(milvus_config.get("vector_field_name", "vector")),
        primary_field_name=str(milvus_config.get("primary_field_name", "id")),
    )

  def add(
      self,
      signal_id: str,
      bucket_id: str,
      vector: list[float],
      index_name: str,
  ) -> None:
    collection_name = self._collection(index_name)
    record_id = self._record_id(index_name, signal_id)
    self._delete_existing(collection_name, record_id)
    self.client.insert(
        collection_name=collection_name,
        data=[{
            self.primary_field_name: record_id,
            "signal_id": signal_id,
            "bucket_id": bucket_id,
            self.vector_field_name: vector,
        }],
    )

  def search(
      self,
      vector: list[float],
      top_k: int,
      index_name: str,
  ) -> list[VectorHit]:
    collection_name = self._collection(index_name)
    self._load_collection(collection_name)
    results = self.client.search(
        collection_name=collection_name,
        data=[vector],
        limit=top_k,
        output_fields=["signal_id", "bucket_id"],
        search_params={
            "metric_type": self.metric_type,
            "params": {},
        },
    )
    hits: list[VectorHit] = []
    first_result = results[0] if results else []
    for rank, raw_hit in enumerate(first_result, start=1):
      entity = self._entity(raw_hit)
      hits.append(
          VectorHit(
              signal_id=str(entity.get("signal_id", "")),
              bucket_id=str(entity.get("bucket_id", "")),
              similarity=float(self._score(raw_hit)),
              rank=rank,
              index_name=index_name,
          )
      )
    return hits

  def _ensure_collections(self) -> None:
    for collection_name in self.collections.values():
      if not self.client.has_collection(collection_name):
        self.client.create_collection(
            collection_name=collection_name,
            dimension=self.dimension,
            primary_field_name=self.primary_field_name,
            id_type="string",
            vector_field_name=self.vector_field_name,
            metric_type=self.metric_type,
            auto_id=False,
        )
      self._load_collection(collection_name)

  def _collection(self, index_name: str) -> str:
    if index_name not in self.collections:
      raise ValueError(f"Unknown index name: {index_name}")
    return self.collections[index_name]

  def _delete_existing(self, collection_name: str, record_id: str) -> None:
    escaped_record_id = record_id.replace("\\", "\\\\").replace('"', '\\"')
    self.client.delete(
        collection_name=collection_name,
        filter=f'{self.primary_field_name} == "{escaped_record_id}"',
    )

  def _load_collection(self, collection_name: str) -> None:
    try:
      self.client.load_collection(collection_name=collection_name)
    except Exception:  # pylint: disable=broad-exception-caught
      # Milvus returns an error when a collection is already loaded on some
      # deployments. Search can still proceed in that case.
      return

  @staticmethod
  def _record_id(index_name: str, signal_id: str) -> str:
    return f"{index_name}:{signal_id}"

  @staticmethod
  def _entity(raw_hit: Any) -> dict[str, Any]:
    if isinstance(raw_hit, dict):
      entity = raw_hit.get("entity") or raw_hit.get("data") or raw_hit
      return entity if isinstance(entity, dict) else {}
    entity = getattr(raw_hit, "entity", None)
    if isinstance(entity, dict):
      return entity
    if hasattr(raw_hit, "get"):
      value = raw_hit.get("entity") or raw_hit.get("data")
      return value if isinstance(value, dict) else {}
    return {}

  @staticmethod
  def _score(raw_hit: Any) -> float:
    if isinstance(raw_hit, dict):
      return raw_hit.get("distance", raw_hit.get("score", 0.0))
    if hasattr(raw_hit, "distance"):
      return raw_hit.distance
    if hasattr(raw_hit, "score"):
      return raw_hit.score
    if hasattr(raw_hit, "get"):
      return raw_hit.get("distance", raw_hit.get("score", 0.0))
    return 0.0
