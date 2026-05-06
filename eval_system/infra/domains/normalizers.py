"""KEP-specific normalization helpers."""

from __future__ import annotations

from ..core.normalizers import DefaultNormalizer, RegexTokenizer


class KepNormalizer(DefaultNormalizer):
  """KEP domain normalizer using the v1 default text rules."""

  def __init__(self) -> None:
    """Initialize the KEP normalizer and tokenizer."""
    self.tokenizer = RegexTokenizer()
