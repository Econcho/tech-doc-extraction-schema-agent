from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any


def _to_jsonable(value: Any) -> Any:
  """Convert runtime-observer objects into JSON-safe values."""
  if dataclasses.is_dataclass(value):
    return _to_jsonable(dataclasses.asdict(value))
  if isinstance(value, dict):
    return {key: _to_jsonable(val) for key, val in value.items()}
  if isinstance(value, (list, tuple)):
    return [_to_jsonable(item) for item in value]
  return value


class RuntimeObservationWriter:
  """Writes runtime observation payloads to disk."""

  def write_run(
      self,
      output_dir: str | Path,
      run_id: str,
      payload: dict[str, Any],
  ) -> Path:
    """Write one run bundle into a directory of JSON/JSONL files."""
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "run_meta.json").write_text(
        json.dumps(_to_jsonable(payload["run_meta"]), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    file_map = {
        "blocks": "blocks.jsonl",
        "skipped_blocks": "skipped_blocks.jsonl",
        "containers": "containers.jsonl",
        "chunk_decisions": "chunk_decisions.jsonl",
        "chunks": "chunks.jsonl",
        "prompts": "prompts.jsonl",
        "llm_calls": "llm_calls.jsonl",
        "parses": "parses.jsonl",
        "extractions": "extractions.jsonl",
    }

    for payload_key, filename in file_map.items():
      entries = payload.get(payload_key, [])
      if not entries:
        continue
      lines = [
          json.dumps(_to_jsonable(entry), ensure_ascii=False)
          for entry in entries
      ]
      (run_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return run_dir
