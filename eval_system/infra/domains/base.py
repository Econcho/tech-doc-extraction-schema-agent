"""Domain plugin interface."""

from __future__ import annotations

from typing import Any, Protocol

from ..core.models import EvalContext, EvalDocument


class DomainPlugin(Protocol):
  """Protocol implemented by domain-specific evaluation plugins."""

  name: str

  def get_attribute_policy(self) -> dict[str, str]:
    """Return attribute-key policy categories."""

  def get_allowed_classes(self) -> tuple[str, ...]:
    """Return allowed extraction classes."""

  def get_allowed_attribute_keys(self) -> tuple[str, ...]:
    """Return allowed attribute keys."""

  def get_class_attribute_schema(self) -> dict[str, dict[str, tuple[str, ...]]]:
    """Return per-class required and optional attribute-key schema."""

  def get_attribute_value_schema(self) -> dict[str, dict[str, tuple[str, ...] | None]]:
    """Return per-class allowed attribute values, or None for free-form values."""

  def get_default_metrics(self) -> list[str]:
    """Return the default metric list for this domain."""

  def build_context(self, thresholds: dict[str, float]) -> EvalContext:
    """Build runtime evaluation context."""

  def validate_gold(self, docs: list[EvalDocument]) -> list[str]:
    """Run domain-specific gold validation."""

  def strict_text_match(self, label_text: str, pred_text: str, context: EvalContext) -> bool:
    """Return whether two texts are a strict match."""

  def relaxed_text_match(self, label_text: str, pred_text: str, context: EvalContext) -> bool:
    """Return whether two texts are a relaxed match."""

  def text_similarity(
      self, label_text: str, pred_text: str, context: EvalContext
  ) -> dict[str, float]:
    """Return relaxed text overlap statistics."""

  def strict_attr_match(
      self,
      label_attributes: dict[str, Any],
      pred_attributes: dict[str, Any],
      context: EvalContext,
  ) -> bool:
    """Return whether two attribute sets strictly match."""

  def relaxed_attr_match(
      self,
      label_attributes: dict[str, Any],
      pred_attributes: dict[str, Any],
      context: EvalContext,
  ) -> bool:
    """Return whether two attribute sets relaxed-match."""
