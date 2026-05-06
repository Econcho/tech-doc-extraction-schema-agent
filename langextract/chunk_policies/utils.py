"""Shared helpers for chunk policies."""

from __future__ import annotations

from langextract import chunking
from langextract.core import tokenizer as tokenizer_lib


def token_interval_char_length(
    tokenized_text: tokenizer_lib.TokenizedText,
    token_interval: tokenizer_lib.TokenInterval,
) -> int:
  """Returns the character length covered by a token interval."""
  char_interval = chunking.get_char_interval(tokenized_text, token_interval)
  return max(0, char_interval.end_pos - char_interval.start_pos)
