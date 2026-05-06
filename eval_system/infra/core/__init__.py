"""Core evaluation primitives exposed through the top-level infrastructure layer."""

from .aggregation import Aggregator
from .config import ConfigLoader
from .error_buckets import ErrorBucketAnalyzer
from .matching import MaxWeightBipartiteMatcher, PairRule
from .models import (
    DiagnosticMetricResult,
    ErrorBucketEntry,
    EvalContext,
    EvalDocument,
    EvalExtraction,
    EvaluationSummary,
    MatchResult,
    MetricResult,
    PairMatch,
)
from .normalizers import DefaultNormalizer
from .report import ReportWriter
from .validation import ValidationError, Validator

__all__ = [
    "Aggregator",
    "ConfigLoader",
    "DefaultNormalizer",
    "DiagnosticMetricResult",
    "ErrorBucketAnalyzer",
    "ErrorBucketEntry",
    "EvalContext",
    "EvalDocument",
    "EvalExtraction",
    "EvaluationSummary",
    "MatchResult",
    "MaxWeightBipartiteMatcher",
    "MetricResult",
    "PairMatch",
    "PairRule",
    "ReportWriter",
    "ValidationError",
    "Validator",
]
