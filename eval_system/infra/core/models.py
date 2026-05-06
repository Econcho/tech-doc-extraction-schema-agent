"""Core immutable data models for the evaluation system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalExtraction:
  """Immutable extraction object used internally by the evaluator."""

  extraction_class: str
  extraction_text: str
  attributes: dict[str, Any] = field(default_factory=dict)
  alignment_status: str | None = None


@dataclass(frozen=True)
class EvalDocument:
  """Immutable document object used internally by the evaluator."""

  doc_id: str
  domain: str
  split: str | None
  extractions: tuple[EvalExtraction, ...]
  text: str | None = None
  metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PairMatch:
  """Represents one successful prediction-gold match."""

  pred_index: int
  gold_index: int
  weight: float


@dataclass(frozen=True)
class MatchResult:
  """Stores document-level one-to-one matching results for one metric."""

  metric_name: str
  doc_id: str
  matches: tuple[PairMatch, ...]
  unmatched_pred_indices: tuple[int, ...]
  unmatched_gold_indices: tuple[int, ...]
  tp: int
  fp: int
  fn: int


@dataclass(frozen=True)
class MetricResult:
  """Stores one metric score for one document or one corpus aggregation."""

  metric_name: str
  precision: float
  recall: float
  f1: float
  tp: int
  fp: int
  fn: int


@dataclass(frozen=True)
class DiagnosticMetricResult:
  """Stores one diagnostic metric result that does not use gold matching."""

  metric_name: str
  value: float
  numerator: int
  denominator: int
  details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorBucketEntry:
  """Stores one categorized evaluation error."""

  bucket: str
  doc_id: str
  pred_index: int | None
  gold_index: int | None
  details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalContext:
  """Holds shared runtime state needed by metrics and matchers."""

  domain: str
  thresholds: dict[str, float]
  tokenizer_name: str
  attribute_policy: dict[str, str]
  allowed_classes: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationSummary:
  """Stores the final aggregated evaluation output for one run."""

  dataset_info: dict[str, Any]
  run_info: dict[str, Any]
  micro_results: dict[str, MetricResult]
  macro_doc_results: dict[str, MetricResult]
  macro_class_results: dict[str, dict[str, MetricResult]]
  per_doc_results: dict[str, dict[str, MetricResult]]
  diagnostic_results: dict[str, DiagnosticMetricResult]
  per_doc_diagnostic_results: dict[str, dict[str, DiagnosticMetricResult]]
  error_buckets: dict[str, int]
  error_samples: tuple[ErrorBucketEntry, ...]
