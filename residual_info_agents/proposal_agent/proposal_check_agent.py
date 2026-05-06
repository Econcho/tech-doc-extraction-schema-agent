from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

import yaml

from residual_info_agents.clients.openai_client import OpenAIClient
from residual_info_agents.domain.proposal.proposal import ProposalCheckResult
from residual_info_agents.domain.proposal.proposal import ProposalDraft
from residual_info_agents.proposal_storage.jsonl_store import to_jsonable


class ProposalCheckAgent:
  def __init__(self, config: str | Path):
    self.config_path = Path(config)
    self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
    self.skill = self._read_config_text("proposal_check_skill_path")
    self.client = self._build_client()

  def check(
      self,
      schema_description: str,
      proposal: ProposalDraft,
      supporting_signals: list[dict[str, Any]],
  ) -> ProposalCheckResult:
    response = self.client.chat.completions.create(
        model=self.config["model"]["model_name"],
        messages=[
            {"role": "system", "content": self.skill},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "schema_description": schema_description,
                        "proposal": to_jsonable(proposal),
                        "supporting_signals": supporting_signals,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=float(self.config.get("loop", {}).get("temperature", 0.2)),
    )
    content = response.choices[0].message.content or "{}"
    data = self._parse_json_text(content)
    return ProposalCheckResult(
        proposal_id=proposal.proposal_id,
        bucket_id=proposal.bucket_id,
        passed=bool(data.get("passed", False)),
        conflict_type=str(data.get("conflict_type", "none")),
        conflicting_schema_names=list(data.get("conflicting_schema_names", [])),
        reason=str(data.get("reason", "")),
        suggested_action=str(data.get("suggested_action", "revise")),
    )

  def _build_client(self) -> OpenAIClient:
    model_config = self.config.get("model", {})
    api_key = os.environ.get(str(model_config.get("api_key_env", "")))
    return OpenAIClient(
        api_key=api_key,
        base_url=model_config.get("base_url"),
    )

  def _read_config_text(self, key: str) -> str:
    value = self.config.get("skill", {}).get(key)
    if value is None:
      return ""
    path = Path(value)
    if not path.exists():
      path = self.config_path.parents[2] / path
    return path.read_text(encoding="utf-8") if path.exists() else str(value)

  @staticmethod
  def _parse_json_text(text: str) -> dict[str, Any]:
    stripped_text = text.strip()
    fenced_match = re.search(
        r"```(?:json)?\s*(.*?)\s*```", stripped_text, flags=re.DOTALL
    )
    if fenced_match:
      stripped_text = fenced_match.group(1).strip()
    data = json.loads(stripped_text)
    if not isinstance(data, dict):
      raise ValueError("Proposal check output must be a JSON object.")
    return data
