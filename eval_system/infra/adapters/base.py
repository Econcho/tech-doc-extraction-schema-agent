"""Adapter interfaces."""

from __future__ import annotations

from typing import Any, Protocol

from ..core.models import EvalDocument


class DocumentAdapter(Protocol):
  """Converts external inputs into internal evaluation documents."""

  def load(self, source: str, **kwargs: Any) -> list[EvalDocument]:
    """Load one or more internal evaluation documents."""
