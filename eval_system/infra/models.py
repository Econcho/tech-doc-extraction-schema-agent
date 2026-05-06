"""Top-level infrastructure data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GateDecision:
  """Represents a gate decision derived from one evaluation summary."""

  passed: bool
  status: str
  reasons: tuple[str, ...] = ()
  details: dict[str, Any] = field(default_factory=dict)


__all__ = ["GateDecision"]
