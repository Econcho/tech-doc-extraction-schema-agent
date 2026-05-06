"""Prediction-only structure anomaly rate metric."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.models import DiagnosticMetricResult
from ..core.models import EvalDocument
from ..core.models import EvalExtraction


@dataclass
class StructureAnomalyMetric:
  """Computes the fraction of structurally anomalous predicted extractions."""

  name: str = "structure_anomaly_rate"

  def score_document(
      self,
      doc: EvalDocument,
      *,
      allowed_classes: set[str],
      class_attribute_schema: dict[str, dict[str, tuple[str, ...]]],
      attribute_value_schema: dict[str, dict[str, tuple[str, ...] | None]],
  ) -> DiagnosticMetricResult:
    """Score one prediction document."""
    anomalous_count = 0
    anomaly_samples: list[dict[str, object]] = []

    for extraction in doc.extractions:
      reasons = self._get_anomaly_reasons(
          extraction=extraction,
          allowed_classes=allowed_classes,
          class_attribute_schema=class_attribute_schema,
          attribute_value_schema=attribute_value_schema,
      )
      if not reasons:
        continue
      anomalous_count += 1
      if len(anomaly_samples) < 20:
        anomaly_samples.append(
            {
                "extraction_class": extraction.extraction_class,
                "extraction_text": extraction.extraction_text,
                "attributes": extraction.attributes,
                "reasons": reasons,
            }
        )

    denominator = len(doc.extractions)
    value = anomalous_count / denominator if denominator else 0.0
    return DiagnosticMetricResult(
        metric_name=self.name,
        value=value,
        numerator=anomalous_count,
        denominator=denominator,
        details={"samples": anomaly_samples},
    )

  def aggregate(
      self, results: list[DiagnosticMetricResult]
  ) -> DiagnosticMetricResult:
    """Aggregate per-document anomaly counts into one corpus-level rate."""
    numerator = sum(result.numerator for result in results)
    denominator = sum(result.denominator for result in results)
    value = numerator / denominator if denominator else 0.0
    return DiagnosticMetricResult(
        metric_name=self.name,
        value=value,
        numerator=numerator,
        denominator=denominator,
        details={},
    )

  def _get_anomaly_reasons(
      self,
      *,
      extraction: EvalExtraction,
      allowed_classes: set[str],
      class_attribute_schema: dict[str, dict[str, tuple[str, ...]]],
      attribute_value_schema: dict[str, dict[str, tuple[str, ...] | None]],
  ) -> list[str]:
    """Return structure anomaly reasons for one extraction."""
    extraction_class = extraction.extraction_class
    if extraction_class not in allowed_classes:
      return [f"unsupported_class:{extraction_class}"]

    class_schema = class_attribute_schema.get(extraction_class, {})
    allowed_keys = set(class_schema.get("required", ())) | set(
        class_schema.get("optional", ())
    )
    reasons: list[str] = []
    for key, value in extraction.attributes.items():
      if key not in allowed_keys:
        reasons.append(f"illegal_attribute_key:{key}")
        continue
      allowed_values = attribute_value_schema.get(extraction_class, {}).get(key)
      if allowed_values is None:
        continue
      if str(value) not in allowed_values:
        reasons.append(f"illegal_attribute_value:{key}={value}")
    return reasons
