from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from langextract.core.data import CharInterval
from residual_info_agents.domain.proposal.signal import TriageSignal
from residual_info_agents.proposal_storage.jsonl_store import append_jsonl
from residual_info_agents.proposal_storage.jsonl_store import read_jsonl


class SignalStore:
  def __init__(self, path: str | Path):
    self.path = Path(path)

  def append_signal(self, signal: TriageSignal) -> None:
    self.remove_signal(signal.signal_id)
    append_jsonl(self.path, signal)

  def remove_signal(self, signal_id: str) -> None:
    rows = [row for row in read_jsonl(self.path) if row.get("signal_id") != signal_id]
    if not self.path.exists():
      return
    self.path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in rows
        ),
        encoding="utf-8",
    )

  def get_signal(self, signal_id: str) -> TriageSignal:
    for signal in self.list_signals():
      if signal.signal_id == signal_id:
        return signal
    raise ValueError(f"Unknown signal id: {signal_id}")

  def list_signals(self) -> list[TriageSignal]:
    return [self._signal_from_dict(row) for row in read_jsonl(self.path)]

  def list_signals_by_ids(self, signal_ids: list[str]) -> list[TriageSignal]:
    signals = {signal.signal_id: signal for signal in self.list_signals()}
    missing = [signal_id for signal_id in signal_ids if signal_id not in signals]
    if missing:
      raise ValueError(f"Unknown signal ids: {missing}")
    return [signals[signal_id] for signal_id in signal_ids]

  @staticmethod
  def _signal_from_dict(data: dict[str, Any]) -> TriageSignal:
    char_interval = data.get("char_interval")
    interval = None
    if isinstance(char_interval, dict):
      interval = CharInterval(
          start_pos=char_interval.get("start_pos"),
          end_pos=char_interval.get("end_pos"),
      )
    return TriageSignal(
        signal_id=str(data["signal_id"]),
        doc_ref=str(data["doc_ref"]),
        extraction_doc_ref=data.get("extraction_doc_ref"),
        block_id=int(data["block_id"]),
        heading_tree=list(data.get("heading_tree", [])),
        text=str(data.get("text", "")),
        reason=str(data.get("reason", "")),
        conclusion=str(data.get("conclusion", "")),
        related_old_schema_name=str(data.get("related_old_schema_name", "")),
        confidence=float(data.get("confidence", 0.0)),
        source_embedding_text=str(data.get("source_embedding_text", "")),
        reason_embedding_text=str(data.get("reason_embedding_text", "")),
        created_at=str(data.get("created_at", "")),
        char_interval=interval,
    )
