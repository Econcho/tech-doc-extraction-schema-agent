from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RunMeta:
  run_id: str
  doc_id: str
  policy_name: str
  model_name: str
  max_char_buffer: int
  config_snapshot: dict[str, Any]
  observer_config: dict[str, Any]
  pass_index: int = 0
  status: str = "running"
  error_message: str | None = None
  start_time: str | None = None
  end_time: str | None = None
  duration_ms: int | None = None


@dataclass(slots=True)
class BlockRecord:
  block_id: str
  kind: str
  token_start: int
  token_end: int
  heading_level: int | None
  heading_path_block_ids: list[str]
  list_level: int
  indent: int
  raw_text_preview: str | None = None
  raw_text: str | None = None


@dataclass(slots=True)
class SkippedBlockRecord:
  block_id: str
  kind: str
  skip_reason: str
  raw_text_preview: str | None = None
  raw_text: str | None = None


@dataclass(slots=True)
class ContainerRecord:
  container_id: str
  kind: str
  block_ids: list[str]
  token_start: int
  token_end: int
  char_length: int
  context_block_ids: list[str]
  text_preview: str | None = None
  text: str | None = None


@dataclass(slots=True)
class ChunkDecisionRecord:
  step_index: int
  candidate_container_id: str
  current_container_ids: list[str]
  current_length: int
  candidate_length: int
  merged_length: int
  within_max_char_buffer: bool
  within_max_containers: bool | None = None
  within_max_container_types: bool | None = None
  current_fill_ratio: float | None = None
  decision: str = "merge"


@dataclass(slots=True)
class ChunkRecord:
  chunk_id: str
  container_ids: list[str]
  token_start: int
  token_end: int
  char_length: int
  context_refs: list[dict[str, Any]]
  fallback_from_container_id: str | None = None
  chunk_text_preview: str | None = None
  chunk_text: str | None = None


@dataclass(slots=True)
class PromptRecord:
  chunk_id: str
  chunk_char_length: int
  chunk_text_preview: str | None = None
  additional_context_preview: str | None = None
  chunk_text: str | None = None
  additional_context: str | None = None


@dataclass(slots=True)
class LLMCallRecord:
  chunk_id: str
  llm_call_id: str
  model_name: str
  usage: dict[str, int] | None
  raw_output_preview: str | None = None
  raw_output_char_length: int | None = None
  raw_output: str | None = None
  status: str = "success"
  error_message: str | None = None


@dataclass(slots=True)
class ParseRecord:
  chunk_id: str
  llm_call_id: str | None
  parse_status: str
  error_type: str | None = None
  error_message: str | None = None
  parsed_extraction_count: int = 0


@dataclass(slots=True)
class ExtractionRecord:
  chunk_id: str
  llm_call_id: str | None
  extraction_index_in_chunk: int
  extraction_class: str
  extraction_text_preview: str | None = None
  extraction_text: str | None = None
  attributes: dict[str, Any] | None = None
