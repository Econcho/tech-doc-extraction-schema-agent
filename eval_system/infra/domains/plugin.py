"""KEP domain plugin implementation."""

from __future__ import annotations

from typing import Any

from ..core.models import EvalContext, EvalDocument
from .defaults import (
    ALLOWED_ATTRIBUTE_KEYS,
    ALLOWED_CLASSES,
    ATTRIBUTE_VALUE_SCHEMA,
    CLASS_ATTRIBUTE_SCHEMA,
    DEFAULT_THRESHOLDS,
)
from .normalizers import KepNormalizer
from .validators import KepGoldValidator


class KepDomainPlugin:
  """Domain plugin implementing KEP-specific evaluation rules."""

  name = "kep_v1"

  def __init__(self) -> None:
    """Initialize the KEP domain plugin."""
    self.normalizer = KepNormalizer()
    self.validator = KepGoldValidator()

  def get_attribute_policy(self) -> dict[str, str]:
    """Return the v1 KEP attribute policy."""
    return {key: "scoreable_required" for key in ALLOWED_ATTRIBUTE_KEYS}

  def get_allowed_classes(self) -> tuple[str, ...]:
    """Return all allowed KEP extraction classes."""
    return ALLOWED_CLASSES

  def get_allowed_attribute_keys(self) -> tuple[str, ...]:
    """Return all allowed KEP attribute keys."""
    return ALLOWED_ATTRIBUTE_KEYS

  def get_class_attribute_schema(self) -> dict[str, dict[str, tuple[str, ...]]]:
    """Return the per-class attribute schema for KEP v1."""
    return CLASS_ATTRIBUTE_SCHEMA

  def get_attribute_value_schema(self) -> dict[str, dict[str, tuple[str, ...] | None]]:
    """Return the per-class allowed attribute values for KEP v1."""
    return ATTRIBUTE_VALUE_SCHEMA

  def get_default_metrics(self) -> list[str]:
    """Return the default KEP metrics."""
    return [
        "detection_strict",
        "detection_relaxed",
        "class_strict",
        "class_relaxed",
        "structured_strict",
        "structured_relaxed",
    ]

  def build_context(self, thresholds: dict[str, float]) -> EvalContext:
    """Build an evaluation context for KEP runs."""
    merged_thresholds = {**DEFAULT_THRESHOLDS, **thresholds}
    return EvalContext(
        domain="kep",
        thresholds=merged_thresholds,
        tokenizer_name=self.normalizer.tokenizer.__class__.__name__,
        attribute_policy=self.get_attribute_policy(),
        allowed_classes=self.get_allowed_classes(),
    )

  def validate_gold(self, docs: list[EvalDocument]) -> list[str]:
    """Run domain-specific KEP gold validation."""
    return self.validator.validate(docs)

  def strict_text_match(self, label_text: str, pred_text: str, context: EvalContext) -> bool:
    """Return whether two texts strictly match after normalization."""
    return self.normalizer.normalize_text(label_text) == self.normalizer.normalize_text(pred_text)

  def relaxed_text_match(self, label_text: str, pred_text: str, context: EvalContext) -> bool:
    """Return whether two texts relaxed-match under the KEP thresholds."""
    normalized_label = self.normalizer.normalize_text(label_text)
    normalized_pred = self.normalizer.normalize_text(pred_text)
    stats = self.text_similarity(label_text, pred_text, context)

    if normalized_pred in normalized_label and stats["recall"] > context.thresholds["substring_recall"]:
      return True
    if normalized_label in normalized_pred and stats["precision"] > context.thresholds["substring_precision"]:
      return True
    return (
        stats["f1"] > context.thresholds["text_relaxed_f1"]
        and stats["lccs_ratio"] > context.thresholds["lccs_ratio"]
    )

  def text_similarity(
      self, label_text: str, pred_text: str, context: EvalContext
  ) -> dict[str, float]:
    """Return relaxed text statistics for two texts."""
    return self.normalizer.token_overlap_stats(
        label_text,
        pred_text,
        self.normalizer.tokenizer,
    )

  def strict_attr_match(
      self,
      label_attributes: dict[str, Any],
      pred_attributes: dict[str, Any],
      context: EvalContext,
  ) -> bool:
    """Return whether two attribute dictionaries strictly match."""
    policy = context.attribute_policy
    keys = [
        key
        for key in label_attributes
        if policy.get(key, "scoreable_required") == "scoreable_required"
    ]
    if set(keys) != {key for key in pred_attributes if key in keys}:
      return False
    for key in keys:
      if self.normalizer.normalize_value(label_attributes[key]) != self.normalizer.normalize_value(
          pred_attributes[key]
      ):
        return False
    return True

  def relaxed_attr_match(
      self,
      label_attributes: dict[str, Any],
      pred_attributes: dict[str, Any],
      context: EvalContext,
  ) -> bool:
    """Return whether two attribute dictionaries relaxed-match."""
    return self.strict_attr_match(label_attributes, pred_attributes, context)
