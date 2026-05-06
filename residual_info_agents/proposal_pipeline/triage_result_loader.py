from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any


@dataclasses.dataclass
class TriageConclusion:
  block_id: int
  conclusion: str
  reason: str
  related_old_schema_name: str
  confidence: float


class TriageResultLoader:
  PROPOSAL_CONCLUSIONS = {"new_schema", "new_attr"}

  def load(self, path: str | Path) -> list[TriageConclusion]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
      raw_conclusions = data.get("conclusions", [])
    elif isinstance(data, list):
      raw_conclusions = data
    else:
      raise ValueError("Triage conclusion file must be a JSON object or list.")

    conclusions = []
    for item in raw_conclusions:
      if not isinstance(item, dict):
        continue
      conclusion = str(item.get("conclusion", ""))
      if conclusion not in self.PROPOSAL_CONCLUSIONS:
        continue
      conclusions.append(
          TriageConclusion(
              block_id=int(item["block_id"]),
              conclusion=conclusion,
              reason=str(item.get("reason", "")),
              related_old_schema_name=str(
                  item.get("related_old_schema_name", "")
              ),
              confidence=float(item.get("confidence", 0.0)),
          )
      )
    return conclusions


def default_conclusion_path() -> Path:
  typo_path = Path("residual_info_agents/triage_agent/.conlusions/conclusion.json")
  normal_path = Path("residual_info_agents/triage_agent/.conclusions/conclusion.json")
  if normal_path.exists():
    return normal_path
  return typo_path
