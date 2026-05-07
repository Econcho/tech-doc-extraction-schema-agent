from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RuntimeObservationReader:
  """Reads runtime observation bundles from disk."""

  def read_run(self, run_dir: str | Path) -> dict[str, Any]:
    """Read one run directory produced by RuntimeObservationWriter."""
    base = Path(run_dir)
    payload: dict[str, Any] = {}
    meta_path = base / "run_meta.json"
    if meta_path.exists():
      payload["run_meta"] = json.loads(meta_path.read_text(encoding="utf-8"))

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
      path = base / filename
      if not path.exists():
        payload[payload_key] = []
        continue
      payload[payload_key] = [
          json.loads(line)
          for line in path.read_text(encoding="utf-8").splitlines()
          if line.strip()
      ]
    return payload
