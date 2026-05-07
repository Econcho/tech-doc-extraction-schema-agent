"""Base types for chunk policies."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from langextract import chunking
from langextract.core import data
from langextract.core import tokenizer as tokenizer_lib


@dataclass(slots=True)
class PolicyConfig:
  """Configuration knobs for structure-aware chunk assembly."""

  min_fill_ratio: float = 0.6
  preferred_fill_ratio: float = 1
  max_containers_per_chunk: int = 10
  max_container_types_per_chunk: int = 10
  skip_toc: bool = True
  skip_checklist: bool = True
  skip_code_fence: bool = True
  skip_table: bool = True


class ChunkPolicy(Protocol):
  """Protocol implemented by all chunk policies."""

  def iter_chunks(
      self,
      document: data.Document,
      max_char_buffer: int,
      tokenizer_impl: tokenizer_lib.Tokenizer,
  ) -> Iterator[chunking.TextChunk]:
    """Yields chunks for a source document."""
