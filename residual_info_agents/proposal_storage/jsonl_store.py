from __future__ import annotations

import dataclasses
import enum
import json
from pathlib import Path
from typing import Any

from langextract.core.data import CharInterval


def to_jsonable(value: Any) -> Any:
  if dataclasses.is_dataclass(value):
    return to_jsonable(dataclasses.asdict(value))
  if isinstance(value, CharInterval):
    return {"start_pos": value.start_pos, "end_pos": value.end_pos}
  if isinstance(value, enum.Enum):
    return value.value
  if isinstance(value, Path):
    return str(value)
  if isinstance(value, dict):
    return {str(key): to_jsonable(item) for key, item in value.items()}
  if isinstance(value, (list, tuple)):
    return [to_jsonable(item) for item in value]
  return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
  if not path.exists():
    return []
  rows: list[dict[str, Any]] = []
  for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
      continue
    rows.append(json.loads(line))
  return rows


def append_jsonl(path: Path, value: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a", encoding="utf-8") as file:
    file.write(json.dumps(to_jsonable(value), ensure_ascii=False) + "\n")
