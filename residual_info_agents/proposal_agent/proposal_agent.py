from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import yaml

if __package__ is None or __package__ == "":
  sys.path.append(str(Path(__file__).resolve().parents[2]))

from residual_info_agents.clients.openai_client import OpenAIClient
from residual_info_agents.domain.proposal.enums import BucketStatus
from residual_info_agents.domain.proposal.proposal import ProposalDraft
from residual_info_agents.domain.proposal.proposal import ProposedAttribute
from residual_info_agents.domain.proposal.runtime import ProposalWorkingContext
from residual_info_agents.domain.proposal.signal import SignalInfoRuntimeBlock
from residual_info_agents.domain.proposal.signal import TriageSignal
from residual_info_agents.domain.tools.tool_request import ToolRequest
from residual_info_agents.proposal_agent.proposal_check_agent import (
    ProposalCheckAgent,
)
from residual_info_agents.proposal_storage.bucket_store import BucketStore
from residual_info_agents.proposal_storage.proposal_store import ProposalStore
from residual_info_agents.proposal_storage.signal_store import SignalStore
from residual_info_agents.proposal_storage.jsonl_store import to_jsonable
from residual_info_agents.tools.tool_handler import ToolHandler


def utc_now() -> str:
  return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class ProposalAgent:
  def __init__(self, config: str | Path, tools: str | Path):
    self.config_path = Path(config)
    self.tools_path = Path(tools)
    self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
    self.tools = json.loads(self.tools_path.read_text(encoding="utf-8"))
    self.skill = self._read_config_text("proposal_agent_skill_path")
    self.client = self._build_client()
    self.toolhandler = ToolHandler(self.tools)
    storage = self.config.get("storage", {})
    self.signal_store = SignalStore(storage["signal_store_path"])
    self.bucket_store = BucketStore(storage["bucket_store_path"])
    self.proposal_store = ProposalStore(
        storage["proposal_store_path"],
        storage["proposal_check_store_path"],
    )
    self.working_context: ProposalWorkingContext | None = None

  def build_context(
      self,
      bucket_id: str,
      schema_description: str | Path,
  ) -> ProposalWorkingContext:
    bucket = self.bucket_store.get_bucket(bucket_id)
    signals = self.signal_store.list_signals_by_ids(bucket.member_signal_ids)
    self.working_context = ProposalWorkingContext(
        bucket_id=bucket.bucket_id,
        bucket_type=bucket.type.value,
        schema_description=self._read_text_or_value(schema_description),
        signals=[self._runtime_block(signal) for signal in signals],
        bucket_metadata=bucket,
    )
    return self.working_context

  def main_loop(
      self,
      bucket_id: str,
      schema_description: str | Path,
  ) -> dict[str, Any]:
    context = self.build_context(bucket_id, schema_description)
    max_turns = int(self.config.get("loop", {}).get("max_turns", 4))
    for turn in range(max_turns):
      context.turn_count = turn
      response = self.client.chat.completions.create(
          model=self.config["model"]["model_name"],
          messages=self._build_messages(),
          response_format={"type": "json_object"},
          tools=self.tools,
          temperature=float(
              self.config.get("loop", {}).get("temperature", 0.2)
          ),
      )
      message = response.choices[0].message
      content = message.content
      tool_calls = message.tool_calls
      if content:
        data = self._parse_json_text(content)
        if data.get("action") == "split_required":
          self.bucket_store.update_status(bucket_id, BucketStatus.AMBIGUOUS)
          return {"action": "split_required", "result": data}
        proposal = self._proposal_from_output(data)
        self.proposal_store.save_proposal_draft(proposal)
        check = ProposalCheckAgent(self.config_path).check(
            context.schema_description,
            proposal,
            [to_jsonable(signal) for signal in context.signals],
        )
        self.proposal_store.save_proposal_check(check)
        if check.passed:
          self.bucket_store.update_status(bucket_id, BucketStatus.STABLE)
        else:
          self.bucket_store.update_status(bucket_id, BucketStatus.AMBIGUOUS)
        return {
            "proposal": to_jsonable(proposal),
            "check": to_jsonable(check),
        }

      if not tool_calls:
        break
      for tool_call in tool_calls:
        tool_request = self.build_tool_request(tool_call)
        tool_request.args.update(self._runtime_tool_args(tool_request))
        tool_result = self.toolhandler.handle_tool_call(tool_request)
        context.tool_results.append(tool_result)

    return {"context": to_jsonable(context)}

  def build_tool_request(self, openai_tool_call: Any) -> ToolRequest:
    tool_call_data = self._normalize_openai_tool_call(openai_tool_call)
    function = tool_call_data.get("function")
    if not isinstance(function, dict):
      raise ValueError("OpenAI tool call must contain function.")
    args = self._parse_tool_arguments(function.get("arguments", {}))
    return ToolRequest(
        tool_use_id=str(tool_call_data.get("id", "")),
        tool_name=str(function.get("name")),
        args=args,
    )

  def _build_client(self) -> OpenAIClient:
    model_config = self.config.get("model", {})
    api_key = os.environ.get(str(model_config.get("api_key_env", "")))
    return OpenAIClient(
        api_key=api_key,
        base_url=model_config.get("base_url"),
    )

  def _build_messages(self) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": self.skill},
        {
            "role": "user",
            "content": json.dumps(
                to_jsonable(self.working_context),
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]

  def _runtime_tool_args(self, tool_request: ToolRequest) -> dict[str, Any]:
    if self.working_context is None:
      raise ValueError("working_context has not been built.")
    requested_ids = tool_request.args.get("resblock_ids", [])
    if not isinstance(requested_ids, list):
      raise ValueError("Tool request args must contain resblock_ids list.")
    requested_id_set = {int(block_id) for block_id in requested_ids}
    selected = [
        signal
        for signal in self.working_context.signals
        if signal.resblock_id in requested_id_set
    ]
    if len(selected) != len(requested_ids):
      raise ValueError(f"Unknown requested resblock ids: {requested_ids}")
    doc_refs = {signal.doc_ref for signal in selected}
    extraction_refs = {
        signal.extraction_doc_ref
        for signal in selected
        if signal.extraction_doc_ref is not None
    }
    if len(doc_refs) != 1:
      raise ValueError("One tool call cannot span multiple source documents.")
    runtime_args = {
        "doc_ref": Path(next(iter(doc_refs))),
        "resblocks": [
            {
                "block_id": signal.resblock_id,
                "text": signal.text,
                "heading_tree": signal.heading_tree,
                "char_interval": to_jsonable(signal.char_interval),
            }
            for signal in selected
        ],
    }
    if extraction_refs:
      if len(extraction_refs) != 1:
        raise ValueError(
            "One tool call cannot span multiple extraction documents."
        )
      runtime_args["extraction_doc_ref"] = Path(next(iter(extraction_refs)))
    return runtime_args

  def _proposal_from_output(self, data: dict[str, Any]) -> ProposalDraft:
    if self.working_context is None:
      raise ValueError("working_context has not been built.")
    proposal_data = data.get("proposal", data)
    if not isinstance(proposal_data, dict):
      raise ValueError("Proposal output must contain a proposal object.")
    return ProposalDraft(
        proposal_id=f"proposal_{self.working_context.bucket_id}_{utc_now()}",
        bucket_id=self.working_context.bucket_id,
        proposal_type=str(
            proposal_data.get("proposal_type", self.working_context.bucket_type)
        ),
        proposed_name=str(proposal_data.get("proposed_name", "")),
        definition=str(proposal_data.get("definition", "")),
        motivation=str(proposal_data.get("motivation", "")),
        related_old_schema_name=str(
            proposal_data.get("related_old_schema_name", "")
        ),
        supporting_signal_ids=list(proposal_data.get("supporting_signal_ids", [])),
        representative_examples=list(
            proposal_data.get("representative_examples", [])
        ),
        attributes=[
            ProposedAttribute(
                name=str(item.get("name", "")),
                description=str(item.get("description", "")),
                value_type=str(item.get("value_type", "string")),
                required=bool(item.get("required", False)),
            )
            for item in proposal_data.get("attributes", [])
            if isinstance(item, dict)
        ],
        confidence=float(proposal_data.get("confidence", 0.0)),
        risk_flags=list(proposal_data.get("risk_flags", [])),
        created_at=utc_now(),
    )

  @staticmethod
  def _runtime_block(signal: TriageSignal) -> SignalInfoRuntimeBlock:
    return SignalInfoRuntimeBlock(
        signal_id=signal.signal_id,
        doc_ref=signal.doc_ref,
        extraction_doc_ref=signal.extraction_doc_ref,
        resblock_id=signal.block_id,
        heading_tree=signal.heading_tree,
        text=signal.text,
        char_interval=signal.char_interval,
    )

  def _read_config_text(self, key: str) -> str:
    value = self.config.get("skill", {}).get(key)
    return self._read_text_or_value(value)

  def _read_text_or_value(self, value: str | Path | None) -> str:
    if value is None:
      return ""
    path = Path(value)
    if not path.exists():
      path = self.config_path.parents[2] / path
    return path.read_text(encoding="utf-8") if path.exists() else str(value)

  @staticmethod
  def _normalize_openai_tool_call(openai_tool_call: Any) -> dict[str, Any]:
    if hasattr(openai_tool_call, "model_dump"):
      tool_call_data = openai_tool_call.model_dump()
      if isinstance(tool_call_data, dict):
        return tool_call_data
    if isinstance(openai_tool_call, dict):
      return openai_tool_call
    raise TypeError(
        f"Unsupported OpenAI tool call type: {type(openai_tool_call)!r}"
    )

  @staticmethod
  def _parse_tool_arguments(arguments: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(arguments, dict):
      return dict(arguments)
    if isinstance(arguments, str):
      parsed = json.loads(arguments) if arguments.strip() else {}
      if not isinstance(parsed, dict):
        raise ValueError("Tool arguments JSON must decode to an object.")
      return parsed
    raise TypeError(f"Unsupported tool arguments type: {type(arguments)!r}")

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
      raise ValueError("Proposal output must be a JSON object.")
    return data
