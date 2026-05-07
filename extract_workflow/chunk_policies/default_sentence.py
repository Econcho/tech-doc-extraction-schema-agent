"""Default sentence chunking policy."""

from __future__ import annotations

from collections.abc import Iterator

from langextract import chunking
from langextract.core import data
from langextract.core import tokenizer as tokenizer_lib


class SentenceChunkPolicy:
  """Delegates chunking to the existing sentence-based iterator."""

  def iter_chunks(
      self,
      document: data.Document,
      max_char_buffer: int,
      tokenizer_impl: tokenizer_lib.Tokenizer,
  ) -> Iterator[chunking.TextChunk]:
    """Yields chunks using the legacy sentence-first logic."""
    yield from chunking.ChunkIterator(
        text=document.tokenized_text,
        max_char_buffer=max_char_buffer,
        document=document,
        tokenizer_impl=tokenizer_impl,
    )
