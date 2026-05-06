"""Aggregation helpers for micro and macro metrics."""

from __future__ import annotations

from collections import defaultdict

from .models import MatchResult, MetricResult


class Aggregator:
  """Aggregates document-level match results into corpus-level metrics."""

  def build_metric_result(self, metric_name: str, tp: int, fp: int, fn: int) -> MetricResult:
    """Convert raw counts to a precision/recall/F1 object."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return MetricResult(metric_name, precision, recall, f1, tp, fp, fn)

  def aggregate_micro(self, metric_name: str, match_results: list[MatchResult]) -> MetricResult:
    """Aggregate counts across all documents before scoring."""
    tp = sum(result.tp for result in match_results)
    fp = sum(result.fp for result in match_results)
    fn = sum(result.fn for result in match_results)
    return self.build_metric_result(metric_name, tp, fp, fn)

  def aggregate_macro_doc(
      self, metric_name: str, match_results: list[MatchResult]
  ) -> MetricResult:
    """Average document-level P/R/F1 scores equally across documents."""
    if not match_results:
      return self.build_metric_result(metric_name, 0, 0, 0)

    per_doc = [
        self.build_metric_result(metric_name, result.tp, result.fp, result.fn)
        for result in match_results
    ]
    return MetricResult(
        metric_name=metric_name,
        precision=sum(item.precision for item in per_doc) / len(per_doc),
        recall=sum(item.recall for item in per_doc) / len(per_doc),
        f1=sum(item.f1 for item in per_doc) / len(per_doc),
        tp=sum(item.tp for item in per_doc),
        fp=sum(item.fp for item in per_doc),
        fn=sum(item.fn for item in per_doc),
    )

  def aggregate_macro_class(
      self,
      metric_name: str,
      per_class_results: dict[str, list[MatchResult]],
  ) -> dict[str, MetricResult]:
    """Aggregate metric results separately for each extraction class."""
    return {
        extraction_class: self.aggregate_micro(metric_name, results)
        for extraction_class, results in per_class_results.items()
    }

  def bucket_by_class(
      self, match_results: list[tuple[str, MatchResult]]
  ) -> dict[str, list[MatchResult]]:
    """Group match results by extraction class for macro-class reporting."""
    buckets: dict[str, list[MatchResult]] = defaultdict(list)
    for extraction_class, result in match_results:
      buckets[extraction_class].append(result)
    return dict(buckets)
