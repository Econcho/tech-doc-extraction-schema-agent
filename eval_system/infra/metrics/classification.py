"""Classification metrics."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.models import EvalContext, MatchResult, MetricResult
from ..domains.base import DomainPlugin
from .base import Metric
from .utils import ClassRule


@dataclass
class ClassificationMetric(Metric):
  """Classification metric implementation."""

  name: str
  relaxed: bool
  plugin: DomainPlugin

  def build_pair_rule(self, context: EvalContext) -> ClassRule:
    """Build the classification pair rule."""
    return ClassRule(context=context, plugin=self.plugin, relaxed=self.relaxed)

  def score(self, match_result: MatchResult) -> MetricResult:
    """Score one document from one classification match result."""
    tp = match_result.tp
    fp = match_result.fp
    fn = match_result.fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return MetricResult(self.name, precision, recall, f1, tp, fp, fn)
