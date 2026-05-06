"""Shared pair-rule utilities for metrics."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.matching import PairRule
from ..core.models import EvalContext, EvalExtraction
from ..domains.base import DomainPlugin


@dataclass
class BaseRule:
  """Base implementation shared by concrete metric pair rules."""

  context: EvalContext
  plugin: DomainPlugin


@dataclass
class DetectionRule(BaseRule, PairRule):
  """Pair rule for detection metrics."""

  relaxed: bool

  def is_legal(self, pred: EvalExtraction, gold: EvalExtraction) -> bool:
    """Check text-only legality."""
    if self.relaxed:
      return self.plugin.relaxed_text_match(pred.extraction_text, gold.extraction_text, self.context)
    return self.plugin.strict_text_match(pred.extraction_text, gold.extraction_text, self.context)

  def weight(self, pred: EvalExtraction, gold: EvalExtraction) -> float:
    """Return either 1.0 or relaxed text F1."""
    if not self.relaxed:
      return 1.0
    return self.plugin.text_similarity(pred.extraction_text, gold.extraction_text, self.context)["f1"]


@dataclass
class ClassRule(BaseRule, PairRule):
  """Pair rule for class metrics."""

  relaxed: bool

  def is_legal(self, pred: EvalExtraction, gold: EvalExtraction) -> bool:
    """Check text and class legality."""
    if pred.extraction_class != gold.extraction_class:
      return False
    if self.relaxed:
      return self.plugin.relaxed_text_match(pred.extraction_text, gold.extraction_text, self.context)
    return self.plugin.strict_text_match(pred.extraction_text, gold.extraction_text, self.context)

  def weight(self, pred: EvalExtraction, gold: EvalExtraction) -> float:
    """Return either 1.0 or relaxed text F1."""
    if not self.relaxed:
      return 1.0
    return self.plugin.text_similarity(pred.extraction_text, gold.extraction_text, self.context)["f1"]


@dataclass
class StructuredRule(BaseRule, PairRule):
  """Pair rule for structured metrics."""

  relaxed: bool

  def is_legal(self, pred: EvalExtraction, gold: EvalExtraction) -> bool:
    """Check class, text, and attribute legality."""
    if pred.extraction_class != gold.extraction_class:
      return False
    if self.relaxed:
      text_ok = self.plugin.relaxed_text_match(
          pred.extraction_text, gold.extraction_text, self.context
      )
    else:
      text_ok = self.plugin.strict_text_match(
          pred.extraction_text, gold.extraction_text, self.context
      )
    if not text_ok:
      return False
    return self.plugin.strict_attr_match(pred.attributes, gold.attributes, self.context)

  def weight(self, pred: EvalExtraction, gold: EvalExtraction) -> float:
    """Return either 1.0 or relaxed text F1."""
    if not self.relaxed:
      return 1.0
    return self.plugin.text_similarity(pred.extraction_text, gold.extraction_text, self.context)["f1"]
