from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from langextract.core.data import CharInterval
from residual_info_agents.domain.proposal.signal import TriageSignal
from residual_info_agents.proposal_pipeline.triage_result_loader import (
    TriageConclusion,
)


def utc_now() -> str:
  return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class SignalBuilder:
  def build_from_files(
      self,
      residual_info_json: str | Path,
      conclusions: list[TriageConclusion],
  ) -> list[TriageSignal]:
    data = json.loads(Path(residual_info_json).read_text(encoding="utf-8"))
    blocks_by_id = {
        int(block["block_id"]): block
        for block in data.get("resblocks", [])
        if "block_id" in block
    }
    signals = []
    for conclusion in conclusions:
      if conclusion.block_id not in blocks_by_id:
        raise ValueError(
            f"Conclusion references missing block: {conclusion.block_id}"
        )
      block = blocks_by_id[conclusion.block_id]
      heading_tree = list(block.get("heading_tree", []))
      text = str(block.get("text", ""))
      signals.append(
          TriageSignal(
              signal_id=self._signal_id(
                  str(data.get("original_doc_ref", "")),
                  conclusion.block_id,
                  conclusion.conclusion,
              ),
              doc_ref=str(data.get("original_doc_ref", "")),
              extraction_doc_ref=data.get("extraction_doc_ref"),
              block_id=conclusion.block_id,
              heading_tree=heading_tree,
              text=text,
              reason=conclusion.reason,
              conclusion=conclusion.conclusion,
              related_old_schema_name=conclusion.related_old_schema_name,
              confidence=conclusion.confidence,
              source_embedding_text="\n".join(heading_tree + [text]),
              reason_embedding_text=conclusion.reason,
              created_at=utc_now(),
              char_interval=self._char_interval(block),
          )
      )
    return signals

  @staticmethod
  def _signal_id(doc_ref: str, block_id: int, conclusion: str) -> str:
    source = f"{doc_ref}:{block_id}:{conclusion}".encode("utf-8")
    return "sig_" + hashlib.sha1(source).hexdigest()[:16]

  @staticmethod
  def _char_interval(block: dict[str, Any]) -> CharInterval | None:
    interval = block.get("char_interval")
    if not isinstance(interval, dict):
      return None
    return CharInterval(
        start_pos=interval.get("start_pos"),
        end_pos=interval.get("end_pos"),
    )
