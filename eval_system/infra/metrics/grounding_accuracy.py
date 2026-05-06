"""Prediction-only grounding accuracy rate diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.models import DiagnosticMetricResult
from ..core.models import EvalDocument


_GROUNDING_METRIC_NAMES = (
    "grounding_match_exact_rate",
    "grounding_match_lesser_rate",
    "grounding_match_fuzzy_rate",
    "grounding_match_none_rate",
)


@dataclass
class GroundingAccuracyMetric:
  """Computes grounding-status distribution rates from prediction metadata."""

  metric_names: tuple[str, ...] = _GROUNDING_METRIC_NAMES

  def score_document(
      self,
      doc: EvalDocument,
  ) -> dict[str, DiagnosticMetricResult]:
    """Score one prediction document for grounding status rates."""
    counts = {
        "match_exact": 0,
        "match_lesser": 0,
        "match_fuzzy": 0,
        "match_none": 0,
    }
    for extraction in doc.extractions:
      status = self._normalize_status(extraction.alignment_status)
      counts[status] += 1

    denominator = len(doc.extractions)
    return {
        "grounding_match_exact_rate": self._build_result(
            "grounding_match_exact_rate", counts["match_exact"], denominator
        ),
        "grounding_match_lesser_rate": self._build_result(
            "grounding_match_lesser_rate", counts["match_lesser"], denominator
        ),
        "grounding_match_fuzzy_rate": self._build_result(
            "grounding_match_fuzzy_rate", counts["match_fuzzy"], denominator
        ),
        "grounding_match_none_rate": self._build_result(
            "grounding_match_none_rate", counts["match_none"], denominator
        ),
    }

  def aggregate(
      self,
      results: list[dict[str, DiagnosticMetricResult]],
  ) -> dict[str, DiagnosticMetricResult]:
    """Aggregate document-level grounding diagnostics."""
    aggregated: dict[str, DiagnosticMetricResult] = {}
    for metric_name in self.metric_names:
      numerator = sum(result[metric_name].numerator for result in results)
      denominator = sum(result[metric_name].denominator for result in results)
      aggregated[metric_name] = self._build_result(
          metric_name, numerator, denominator
      )
    return aggregated

  def _build_result(
      self,
      metric_name: str,
      numerator: int,
      denominator: int,
  ) -> DiagnosticMetricResult:
    """Build one diagnostic metric result."""
    value = numerator / denominator if denominator else 0.0
    return DiagnosticMetricResult(
        metric_name=metric_name,
        value=value,
        numerator=numerator,
        denominator=denominator,
        details={},
    )

  def _normalize_status(self, status: str | None) -> str:
    """Normalize one alignment status string to a grounding bucket."""
    if status is None:
      return "match_none"
    normalized = str(status).strip().lower()
    if normalized in {"match_exact", "match_lesser", "match_fuzzy"}:
      return normalized
    return "match_none"
