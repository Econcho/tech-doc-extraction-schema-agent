"""Error bucket analysis for post-evaluation diagnostics."""

from __future__ import annotations

from collections import Counter

from .models import ErrorBucketEntry, EvalExtraction, MatchResult


class ErrorBucketAnalyzer:
  """Classifies unmatched or near-matched extractions into error buckets."""

  def analyze(
      self,
      *,
      doc_id: str,
      preds: list[EvalExtraction],
      golds: list[EvalExtraction],
      detection_relaxed: MatchResult,
      class_relaxed: MatchResult,
      structured_relaxed: MatchResult,
  ) -> list[ErrorBucketEntry]:
    """Create error bucket entries from multiple matching views."""
    entries: list[ErrorBucketEntry] = []
    entries.extend(self._build_miss_entries(doc_id, detection_relaxed))
    entries.extend(self._build_spurious_entries(doc_id, detection_relaxed))
    entries.extend(self._build_duplicate_entries(doc_id, preds))
    entries.extend(self._build_text_drift_entries(doc_id, detection_relaxed, class_relaxed))
    entries.extend(self._build_class_error_entries(doc_id, detection_relaxed, class_relaxed))
    entries.extend(
        self._build_attribute_error_entries(doc_id, class_relaxed, structured_relaxed)
    )
    return entries

  def count(self, entries: list[ErrorBucketEntry]) -> dict[str, int]:
    """Count error buckets for reporting."""
    return dict(Counter(entry.bucket for entry in entries))

  def _build_miss_entries(self, doc_id: str, result: MatchResult) -> list[ErrorBucketEntry]:
    """Create miss entries for unmatched gold extractions."""
    return [
        ErrorBucketEntry("miss", doc_id, None, index)
        for index in result.unmatched_gold_indices
    ]

  def _build_spurious_entries(
      self, doc_id: str, result: MatchResult
  ) -> list[ErrorBucketEntry]:
    """Create spurious entries for unmatched predictions."""
    return [
        ErrorBucketEntry("spurious", doc_id, index, None)
        for index in result.unmatched_pred_indices
    ]

  def _build_duplicate_entries(
      self, doc_id: str, preds: list[EvalExtraction]
  ) -> list[ErrorBucketEntry]:
    """Create duplicate entries for exact repeated predictions."""
    seen: dict[tuple[str, str, tuple[tuple[str, object], ...]], int] = {}
    duplicates: list[ErrorBucketEntry] = []
    for index, pred in enumerate(preds):
      key = (
          pred.extraction_class,
          pred.extraction_text,
          tuple(sorted(pred.attributes.items())),
      )
      if key in seen:
        duplicates.append(
            ErrorBucketEntry(
                "duplicate",
                doc_id,
                index,
                None,
                {"first_pred_index": seen[key]},
            )
        )
      else:
        seen[key] = index
    return duplicates

  def _build_text_drift_entries(
      self,
      doc_id: str,
      detection_relaxed: MatchResult,
      class_relaxed: MatchResult,
  ) -> list[ErrorBucketEntry]:
    """Create text drift entries for relaxed-only class-preserving matches."""
    matched_pairs = {(item.pred_index, item.gold_index) for item in class_relaxed.matches}
    return [
        ErrorBucketEntry("text_drift", doc_id, item.pred_index, item.gold_index)
        for item in detection_relaxed.matches
        if (item.pred_index, item.gold_index) not in matched_pairs
    ]

  def _build_class_error_entries(
      self,
      doc_id: str,
      detection_relaxed: MatchResult,
      class_relaxed: MatchResult,
  ) -> list[ErrorBucketEntry]:
    """Create class error entries for text-near but class-wrong pairs."""
    matched_pairs = {(item.pred_index, item.gold_index) for item in class_relaxed.matches}
    return [
        ErrorBucketEntry("class_error", doc_id, item.pred_index, item.gold_index)
        for item in detection_relaxed.matches
        if (item.pred_index, item.gold_index) not in matched_pairs
    ]

  def _build_attribute_error_entries(
      self,
      doc_id: str,
      class_relaxed: MatchResult,
      structured_relaxed: MatchResult,
  ) -> list[ErrorBucketEntry]:
    """Create attribute error entries for class-correct but structure-wrong matches."""
    matched_pairs = {
        (item.pred_index, item.gold_index) for item in structured_relaxed.matches
    }
    return [
        ErrorBucketEntry("attribute_error", doc_id, item.pred_index, item.gold_index)
        for item in class_relaxed.matches
        if (item.pred_index, item.gold_index) not in matched_pairs
    ]
