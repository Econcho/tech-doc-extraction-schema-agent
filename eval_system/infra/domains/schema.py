"""KEP schema declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KepSchema:
  """Stores KEP v1 schema metadata."""

  version: str = "kep_schema_v1"
  label_policy_version: str = "eval_policy_v1"
