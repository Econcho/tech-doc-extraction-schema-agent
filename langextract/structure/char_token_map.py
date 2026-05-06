"""Helpers for mapping character spans back to token intervals."""

from __future__ import annotations

from bisect import bisect_left
from bisect import bisect_right
from dataclasses import dataclass

from langextract.core import tokenizer as tokenizer_lib


@dataclass(slots=True)
class CharTokenMap:
  """Maps character spans in the original text to token intervals."""

  token_starts: list[int]
  token_ends: list[int]

  @classmethod
  def from_tokenized_text(
      cls, tokenized_text: tokenizer_lib.TokenizedText
  ) -> "CharTokenMap":
    """Builds a map from tokenized text."""
    starts = [token.char_interval.start_pos for token in tokenized_text.tokens]
    ends = [token.char_interval.end_pos for token in tokenized_text.tokens]
    return cls(token_starts=starts, token_ends=ends)

  def char_span_to_token_interval(
      self, start_pos: int, end_pos: int
  ) -> tokenizer_lib.TokenInterval | None:
    """Returns the minimal token interval covering a character span."""
    if start_pos >= end_pos or not self.token_starts:
      return None
    start_index = bisect_right(self.token_ends, start_pos)
    end_index = bisect_left(self.token_starts, end_pos)
    if start_index >= end_index:
      return None
    return tokenizer_lib.TokenInterval(
        start_index=start_index,
        end_index=end_index,
    )
