"""Text and attribute normalization utilities."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter


class RegexTokenizer:
  """Tokenizes English technical text with stable symbol boundaries."""

  _pattern = re.compile(r"[A-Za-z0-9_.:/-]+|[^\s]")

  def tokenize(self, text: str) -> list[str]:
    """Split text into evaluation tokens."""
    return self._pattern.findall(text)


class DefaultNormalizer:
  """Applies v1 default normalization rules from the evaluation spec."""

  def normalize_text(self, text: str) -> str:
    """Normalize text for matching and metric computation."""
    normalized = unicodedata.normalize("NFKC", text)
    # Treat escaped quotes and raw quotes as the same surface form during matching.
    normalized = re.sub(r'\\+"', '"', normalized)
    normalized = normalized.replace("\n", " ").replace("\t", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized

  def normalize_value(self, value: object) -> object:
    """Normalize attribute values recursively."""
    if isinstance(value, str):
      return self.normalize_text(value)
    if isinstance(value, list):
      return [self.normalize_value(item) for item in value]
    if isinstance(value, tuple):
      return [self.normalize_value(item) for item in value]
    if isinstance(value, dict):
      return {
          str(key): self.normalize_value(nested_value)
          for key, nested_value in value.items()
      }
    return value

  def token_overlap_stats(
      self, label_text: str, pred_text: str, tokenizer: RegexTokenizer
  ) -> dict[str, float]:
    """Compute token precision, recall, F1, and LCCS ratio."""
    label_tokens = tokenizer.tokenize(self.normalize_text(label_text))
    pred_tokens = tokenizer.tokenize(self.normalize_text(pred_text))

    label_counter = Counter(label_tokens)
    pred_counter = Counter(pred_tokens)
    overlap_count = sum((label_counter & pred_counter).values())

    precision = overlap_count / len(pred_tokens) if pred_tokens else 0.0
    recall = overlap_count / len(label_tokens) if label_tokens else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    lccs_ratio = self._lccs_ratio(label_tokens, pred_tokens)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "lccs_ratio": lccs_ratio,
    }

  def _lccs_ratio(self, label_tokens: list[str], pred_tokens: list[str]) -> float:
    """Compute the longest common contiguous subsequence ratio."""
    if not label_tokens or not pred_tokens:
      return 0.0

    dp = [[0] * (len(pred_tokens) + 1) for _ in range(len(label_tokens) + 1)]
    longest = 0
    for label_index in range(1, len(label_tokens) + 1):
      for pred_index in range(1, len(pred_tokens) + 1):
        if label_tokens[label_index - 1] == pred_tokens[pred_index - 1]:
          dp[label_index][pred_index] = dp[label_index - 1][pred_index - 1] + 1
          longest = max(longest, dp[label_index][pred_index])
    return longest / min(len(label_tokens), len(pred_tokens))
