from __future__ import annotations

import hashlib
import math
import re


class EmbeddingClient:
  """Small deterministic embedding client for MVP offline routing.

  The config may name external providers, but this implementation deliberately
  keeps a local hash embedding fallback so ingestion is runnable without model
  downloads or network access.
  """

  def __init__(self, dimension: int = 256, **_: object):
    self.dimension = dimension

  def embed_texts(self, texts: list[str]) -> list[list[float]]:
    return [self._embed_text(text) for text in texts]

  def _embed_text(self, text: str) -> list[float]:
    vector = [0.0] * self.dimension
    tokens = re.findall(r"[A-Za-z0-9_./:-]+", text.lower())
    if not tokens:
      return vector
    for token in tokens:
      digest = hashlib.sha256(token.encode("utf-8")).digest()
      index = int.from_bytes(digest[:4], "big") % self.dimension
      sign = 1.0 if digest[4] % 2 == 0 else -1.0
      vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
      return vector
    return [value / norm for value in vector]
