"""Metric interface definitions."""

from __future__ import annotations

from typing import Protocol

from ..core.matching import PairRule
from ..core.models import EvalContext, MatchResult, MetricResult


class Metric(Protocol):
  """Protocol implemented by all metrics."""

  name: str

  def build_pair_rule(self, context: EvalContext) -> PairRule:
    """Build the pair rule used by the matcher."""

  def score(self, match_result: MatchResult) -> MetricResult:
    """Convert a document-level match result into a metric result."""
