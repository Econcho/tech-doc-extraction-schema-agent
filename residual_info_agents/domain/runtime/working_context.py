from __future__ import annotations

import dataclasses
import enum
import json
from pathlib import Path
from typing import Any

from langextract.core.data import CharInterval
from residual_info_agents.domain.runtime.resblock_runtime_info import (
    ResBlockRuntimeInfo,
)
from residual_info_agents.domain.static.residual_block import ResidualBlock


@dataclasses.dataclass
class WorkingContext:
  """Complete working context for the triage agent."""

  original_doc_ref: str | Path
  extraction_doc_ref: str | Path
  schema_description: str
  active_resblocks: list[ResidualBlock]
  block_info: list[ResBlockRuntimeInfo]

  def to_json(self, *, indent: int | None = 2) -> str:
    """Serializes the working context to a JSON string."""

    return json.dumps(
        self._to_jsonable(self),
        ensure_ascii=False,
        indent=indent,
    )

  def build_context_json(self, *, indent: int | None = 2) -> str:
    """Builds the JSON context passed to the triage agent."""

    payload = {
        "schema_description": self.schema_description,
        "active_resblocks": self.active_resblocks,
        "block_info": self.block_info,
    }
    return json.dumps(
        self._to_jsonable(payload),
        ensure_ascii=False,
        indent=indent,
    )

  @classmethod
  def _to_jsonable(cls, value: Any) -> Any:
    if dataclasses.is_dataclass(value):
      return cls._to_jsonable(dataclasses.asdict(value))
    if isinstance(value, CharInterval):
      return {
          "start_pos": value.start_pos,
          "end_pos": value.end_pos,
      }
    if isinstance(value, enum.Enum):
      return value.value
    if isinstance(value, Path):
      return str(value)
    if isinstance(value, dict):
      return {
          str(key): cls._to_jsonable(item)
          for key, item in value.items()
      }
    if isinstance(value, (list, tuple)):
      return [cls._to_jsonable(item) for item in value]
    return value
