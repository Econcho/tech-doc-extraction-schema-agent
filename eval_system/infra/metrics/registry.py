"""Metric registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import Metric


@dataclass
class MetricRegistry:
  """Stores and resolves metric objects by name."""

  _metrics: dict[str, Metric] = field(default_factory=dict)

  def register(self, metric: Metric) -> None:
    """Register one metric instance."""
    self._metrics[metric.name] = metric

  def get(self, name: str) -> Metric:
    """Return one metric by name."""
    return self._metrics[name]

  def names(self) -> list[str]:
    """Return all registered metric names."""
    return list(self._metrics.keys())
