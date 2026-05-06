from __future__ import annotations

import dataclasses
import enum
from typing import Optional


class TriageLabel(str, enum.Enum):
  NOISE = "noise"
  EXISTING_SCHEMA_COVERED = "existing_schema_covered"
  NEW_ATTR = "new_attr"
  NEW_SCHEMA = "new_schema"
  UNCERTAIN = "uncertain"


@dataclasses.dataclass
class TriageResult:
  label: Optional[TriageLabel] = None
  confidence: Optional[float] = None
  reason: Optional[str] = None
  used_tools: list[str] = dataclasses.field(default_factory=list)
  schema_name: Optional[str] = None
