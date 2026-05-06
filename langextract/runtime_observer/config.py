from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Literal

RecordMode = Literal["off", "light", "full"]


@dataclass(slots=True)
class RuntimeObserverConfig:
  """Configuration for runtime observation recording."""

  enabled: bool = False
  output_dir: str = "runtime_observe"
  max_preview_chars: int = 1000
  block_record: RecordMode = "off"
  skipped_block_record: RecordMode = "off"
  container_record: RecordMode = "off"
  chunk_decision_record: RecordMode = "light"
  chunk_record: RecordMode = "light"
  prompt_record: RecordMode = "light"
  llm_call_record: RecordMode = "light"
  parse_record: RecordMode = "light"
  extraction_record: RecordMode = "off"

  @classmethod
  def from_value(
      cls,
      value: RuntimeObserverConfig | dict[str, Any] | str | Path | None,
  ) -> RuntimeObserverConfig | None:
    """Normalize user input into a RuntimeObserverConfig."""
    if value is None:
      return None
    if isinstance(value, cls):
      return value
    if isinstance(value, dict):
      return cls(**value)
    if isinstance(value, (str, Path)):
      return cls.from_file(value)
    raise TypeError(
        "runtime_observer_config must be None, a dict, a file path, or "
        "RuntimeObserverConfig."
    )

  @classmethod
  def from_file(cls, path: str | Path) -> RuntimeObserverConfig:
    """Load one runtime observer config from a JSON file."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
      payload = json.load(f)
    if not isinstance(payload, dict):
      raise TypeError(
          f"Runtime observer config file must contain one JSON object: "
          f"{config_path}"
      )
    return cls(**payload)

  def mode_for(self, field_name: str) -> RecordMode:
    """Return the effective mode for one record type."""
    if not self.enabled:
      return "off"
    return getattr(self, field_name)

  def is_enabled_for(self, field_name: str) -> bool:
    """Return whether one record type is enabled."""
    return self.mode_for(field_name) != "off"

  def snapshot(self) -> dict[str, Any]:
    """Return a JSON-safe config snapshot."""
    return asdict(self)
