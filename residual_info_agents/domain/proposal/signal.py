from __future__ import annotations

import dataclasses

from langextract.core.data import CharInterval


@dataclasses.dataclass
class TriageSignal:
  """A triage conclusion used for proposal bucket routing."""

  signal_id: str
  doc_ref: str
  extraction_doc_ref: str | None
  block_id: int
  heading_tree: list[str]
  text: str
  reason: str
  conclusion: str
  related_old_schema_name: str
  confidence: float
  source_embedding_text: str
  reason_embedding_text: str
  created_at: str
  char_interval: CharInterval | None = None


@dataclasses.dataclass
class SignalInfoRuntimeBlock:
  """Runtime signal block visible to ProposalAgent."""

  signal_id: str
  doc_ref: str
  extraction_doc_ref: str | None
  resblock_id: int
  heading_tree: list[str]
  text: str
  char_interval: CharInterval | None = None
