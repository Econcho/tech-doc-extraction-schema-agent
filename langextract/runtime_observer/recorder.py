from __future__ import annotations

import contextlib
import contextvars
from dataclasses import asdict
from dataclasses import is_dataclass
from datetime import datetime
from pathlib import Path
import threading
from typing import Any
import uuid

from langextract import chunking
from langextract.runtime_observer.config import RuntimeObserverConfig
from langextract.runtime_observer.models import BlockRecord
from langextract.runtime_observer.models import ChunkDecisionRecord
from langextract.runtime_observer.models import ChunkRecord
from langextract.runtime_observer.models import ContainerRecord
from langextract.runtime_observer.models import ExtractionRecord
from langextract.runtime_observer.models import LLMCallRecord
from langextract.runtime_observer.models import ParseRecord
from langextract.runtime_observer.models import PromptRecord
from langextract.runtime_observer.models import RunMeta
from langextract.runtime_observer.models import SkippedBlockRecord
from langextract.runtime_observer.writer import RuntimeObservationWriter

_CURRENT_SESSION: contextvars.ContextVar[DocumentRunRecorder | None] = (
    contextvars.ContextVar("runtime_observer_current_session", default=None)
)


def get_current_observer_session() -> DocumentRunRecorder | None:
  """Return the active observer session for the current execution context."""
  return _CURRENT_SESSION.get()


@contextlib.contextmanager
def activate_observer_session(session: DocumentRunRecorder | None):
  """Temporarily activate one observer session in the current context."""
  token = _CURRENT_SESSION.set(session)
  try:
    yield
  finally:
    _CURRENT_SESSION.reset(token)


class DocumentRunRecorder:
  """Collects runtime observation records for one document run."""

  def __init__(
      self,
      *,
      config: RuntimeObserverConfig,
      doc_id: str,
      policy_name: str,
      model_name: str,
      max_char_buffer: int,
      config_snapshot: dict[str, Any],
      pass_index: int = 0,
      writer: RuntimeObservationWriter | None = None,
  ) -> None:
    self.config = config
    self.doc_id = doc_id
    self.run_id = self._build_run_id(doc_id, pass_index)
    self.run_meta = RunMeta(
        run_id=self.run_id,
        doc_id=doc_id,
        policy_name=policy_name,
        model_name=model_name,
        max_char_buffer=max_char_buffer,
        config_snapshot=config_snapshot,
        observer_config=config.snapshot(),
        pass_index=pass_index,
        status="running",
        start_time=self._now_iso(),
    )
    self.blocks: list[BlockRecord] = []
    self.skipped_blocks: list[SkippedBlockRecord] = []
    self.containers: list[ContainerRecord] = []
    self.chunk_decisions: list[ChunkDecisionRecord] = []
    self.chunks: list[ChunkRecord] = []
    self.prompts: list[PromptRecord] = []
    self.llm_calls: list[LLMCallRecord] = []
    self.parses: list[ParseRecord] = []
    self.extractions: list[ExtractionRecord] = []
    self._writer = writer or RuntimeObservationWriter()
    self._lock = threading.Lock()
    self._chunk_counter = 0
    self._llm_call_counter = 0
    self._decision_counter = 0
    self._closed = False

  def _build_run_id(self, doc_id: str, pass_index: int) -> str:
    """Build a readable and unique run id."""
    safe_doc_id = doc_id.replace("/", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{timestamp}_{safe_doc_id}_p{pass_index}_{suffix}"

  def _now_iso(self) -> str:
    """Return one ISO-like timestamp string."""
    return datetime.now().isoformat(timespec="milliseconds")

  def _preview(self, text: str | None) -> str | None:
    """Build a preview string capped by config.max_preview_chars."""
    if text is None:
      return None
    if len(text) <= self.config.max_preview_chars:
      return text
    return text[: self.config.max_preview_chars]

  def _mode_for(self, record_field: str) -> str:
    """Return the effective mode for one record type."""
    return self.config.mode_for(record_field)

  def _record_enabled(self, record_field: str) -> bool:
    """Return whether one record type is enabled."""
    return self.config.is_enabled_for(record_field)

  def _chunk_text(
      self,
      tokenized_text,
      token_interval,
  ) -> str:
    """Return the source text for one token interval."""
    return chunking.get_token_interval_text(tokenized_text, token_interval)

  def _ensure_chunk_id(self, text_chunk: chunking.TextChunk) -> str:
    """Attach and return a stable chunk id for one TextChunk."""
    chunk_id = getattr(text_chunk, "_runtime_observer_chunk_id", None)
    if chunk_id is None:
      chunk_id = f"chunk_{self._chunk_counter}"
      self._chunk_counter += 1
      setattr(text_chunk, "_runtime_observer_chunk_id", chunk_id)
    return chunk_id

  def ensure_chunk_id(self, text_chunk: chunking.TextChunk) -> str:
    """Public wrapper for retrieving one stable chunk id."""
    return self._ensure_chunk_id(text_chunk)

  def record_block(self, block, tokenized_text) -> None:
    """Record one StructuredBlock."""
    mode = self._mode_for("block_record")
    if mode == "off":
      return
    raw_text = None
    raw_text_preview = None
    if mode == "full":
      raw_text = str(block.metadata.get("raw_text", "")) or self._chunk_text(
          tokenized_text, block.token_interval
      )
    else:
      raw_text_preview = self._preview(str(block.metadata.get("raw_text", "")))
    record = BlockRecord(
        block_id=block.block_id,
        kind=block.kind,
        token_start=block.token_interval.start_index,
        token_end=block.token_interval.end_index,
        heading_level=block.heading_level,
        heading_path_block_ids=list(block.heading_path_block_ids),
        list_level=block.list_level,
        indent=block.indent,
        raw_text_preview=raw_text_preview,
        raw_text=raw_text,
    )
    with self._lock:
      self.blocks.append(record)

  def record_skipped_block(self, block, reason: str) -> None:
    """Record one skipped block."""
    mode = self._mode_for("skipped_block_record")
    if mode == "off":
      return
    raw_text = None
    raw_text_preview = None
    raw = str(block.metadata.get("raw_text", ""))
    if mode == "full":
      raw_text = raw
    else:
      raw_text_preview = self._preview(raw)
    record = SkippedBlockRecord(
        block_id=block.block_id,
        kind=block.kind,
        skip_reason=reason,
        raw_text_preview=raw_text_preview,
        raw_text=raw_text,
    )
    with self._lock:
      self.skipped_blocks.append(record)

  def record_container(self, container, structured_document) -> None:
    """Record one container."""
    mode = self._mode_for("container_record")
    if mode == "off":
      return
    text = None
    text_preview = None
    tokenized_text = structured_document.source_document.tokenized_text
    if mode == "full":
      text = self._chunk_text(tokenized_text, container.token_interval)
    else:
      text_preview = self._preview(
          self._chunk_text(tokenized_text, container.token_interval)
      )
    char_interval = chunking.get_char_interval(
        tokenized_text,
        container.token_interval,
    )
    record = ContainerRecord(
        container_id=container.container_id,
        kind=container.kind,
        block_ids=list(container.block_ids),
        token_start=container.token_interval.start_index,
        token_end=container.token_interval.end_index,
        char_length=max(0, char_interval.end_pos - char_interval.start_pos),
        context_block_ids=list(container.context_block_ids),
        text_preview=text_preview,
        text=text,
    )
    with self._lock:
      self.containers.append(record)

  def record_chunk_decision(self, **payload: Any) -> None:
    """Record one chunk assembly decision."""
    if not self._record_enabled("chunk_decision_record"):
      return
    with self._lock:
      record = ChunkDecisionRecord(
          step_index=self._decision_counter,
          **payload,
      )
      self._decision_counter += 1
      self.chunk_decisions.append(record)

  def record_chunk(
      self,
      text_chunk: chunking.TextChunk,
      *,
      container_ids: list[str],
      fallback_from_container_id: str | None = None,
  ) -> str:
    """Record one final chunk and return its chunk id."""
    mode = self._mode_for("chunk_record")
    chunk_id = self._ensure_chunk_id(text_chunk)
    if mode == "off":
      return chunk_id
    chunk_text = None
    chunk_text_preview = None
    if mode == "full":
      chunk_text = text_chunk.chunk_text
    else:
      chunk_text_preview = self._preview(text_chunk.chunk_text)
    char_interval = text_chunk.char_interval
    context_refs = []
    for context_ref in text_chunk.context_refs:
      ref_payload = {
          "ref_type": context_ref.ref_type,
          "block_ids": list(context_ref.block_ids),
      }
      if mode == "full":
        ref_payload["context_text"] = context_ref.context_text
      else:
        ref_payload["context_text_preview"] = self._preview(
            context_ref.context_text
        )
      context_refs.append(ref_payload)
    record = ChunkRecord(
        chunk_id=chunk_id,
        container_ids=container_ids,
        token_start=text_chunk.token_interval.start_index,
        token_end=text_chunk.token_interval.end_index,
        char_length=max(0, char_interval.end_pos - char_interval.start_pos),
        context_refs=context_refs,
        fallback_from_container_id=fallback_from_container_id,
        chunk_text_preview=chunk_text_preview,
        chunk_text=chunk_text,
    )
    with self._lock:
      self.chunks.append(record)
    return chunk_id

  def record_prompt(
      self,
      *,
      chunk_id: str,
      chunk_text: str,
      additional_context: str | None,
  ) -> None:
    """Record one prompt payload without the template prompt."""
    mode = self._mode_for("prompt_record")
    if mode == "off":
      return
    record = PromptRecord(
        chunk_id=chunk_id,
        chunk_char_length=len(chunk_text),
        chunk_text_preview=self._preview(chunk_text) if mode != "full" else None,
        additional_context_preview=(
            self._preview(additional_context) if mode != "full" else None
        ),
        chunk_text=chunk_text if mode == "full" else None,
        additional_context=additional_context if mode == "full" else None,
    )
    with self._lock:
      self.prompts.append(record)

  def record_llm_call(
      self,
      *,
      chunk_id: str,
      model_name: str,
      raw_output: str | None,
      usage: dict[str, int] | None,
      status: str,
      error_message: str | None = None,
  ) -> str:
    """Record one provider call and return its llm_call_id."""
    with self._lock:
      llm_call_id = f"llm_{self._llm_call_counter}"
      self._llm_call_counter += 1
    mode = self._mode_for("llm_call_record")
    if mode == "off":
      return llm_call_id
    record = LLMCallRecord(
        chunk_id=chunk_id,
        llm_call_id=llm_call_id,
        model_name=model_name,
        usage=usage,
        raw_output_preview=self._preview(raw_output) if mode != "full" else None,
        raw_output_char_length=len(raw_output) if raw_output is not None else None,
        raw_output=raw_output if mode == "full" else None,
        status=status,
        error_message=error_message,
    )
    with self._lock:
      self.llm_calls.append(record)
    return llm_call_id

  def record_parse(
      self,
      *,
      chunk_id: str,
      llm_call_id: str | None,
      parse_status: str,
      error_type: str | None = None,
      error_message: str | None = None,
      parsed_extraction_count: int = 0,
  ) -> None:
    """Record one parse outcome."""
    if not self._record_enabled("parse_record"):
      return
    record = ParseRecord(
        chunk_id=chunk_id,
        llm_call_id=llm_call_id,
        parse_status=parse_status,
        error_type=error_type,
        error_message=error_message,
        parsed_extraction_count=parsed_extraction_count,
    )
    with self._lock:
      self.parses.append(record)

  def record_extraction(
      self,
      *,
      chunk_id: str,
      llm_call_id: str | None,
      extraction_index_in_chunk: int,
      extraction,
  ) -> None:
    """Record one final extraction to chunk mapping."""
    mode = self._mode_for("extraction_record")
    if mode == "off":
      return
    record = ExtractionRecord(
        chunk_id=chunk_id,
        llm_call_id=llm_call_id,
        extraction_index_in_chunk=extraction_index_in_chunk,
        extraction_class=extraction.extraction_class,
        extraction_text_preview=(
            self._preview(extraction.extraction_text) if mode != "full" else None
        ),
        extraction_text=extraction.extraction_text if mode == "full" else None,
        attributes=dict(extraction.attributes or {}),
    )
    with self._lock:
      self.extractions.append(record)

  def close(
      self,
      *,
      status: str,
      error_message: str | None = None,
  ) -> Path | None:
    """Finalize and write this document run once."""
    with self._lock:
      if self._closed:
        return None
      self._closed = True
      self.run_meta.status = status
      self.run_meta.error_message = error_message
      self.run_meta.end_time = self._now_iso()
      if self.run_meta.start_time and self.run_meta.end_time:
        start = datetime.fromisoformat(self.run_meta.start_time)
        end = datetime.fromisoformat(self.run_meta.end_time)
        self.run_meta.duration_ms = int((end - start).total_seconds() * 1000)
      payload = {
          "run_meta": self.run_meta,
          "blocks": self.blocks,
          "skipped_blocks": self.skipped_blocks,
          "containers": self.containers,
          "chunk_decisions": self.chunk_decisions,
          "chunks": self.chunks,
          "prompts": self.prompts,
          "llm_calls": self.llm_calls,
          "parses": self.parses,
          "extractions": self.extractions,
      }
    return self._writer.write_run(self.config.output_dir, self.run_id, payload)


class RuntimeObservationManager:
  """Creates and tracks per-document recorders for one extraction call."""

  def __init__(
      self,
      *,
      config: RuntimeObserverConfig | None,
      model_name: str,
      max_char_buffer: int,
      chunk_policy: Any = None,
      pass_index: int = 0,
  ) -> None:
    self.config = config
    self.model_name = model_name
    self.max_char_buffer = max_char_buffer
    self.chunk_policy = chunk_policy
    self.pass_index = pass_index
    self._writer = RuntimeObservationWriter()
    self._sessions: dict[str, DocumentRunRecorder] = {}

  @property
  def enabled(self) -> bool:
    """Return whether runtime observation is enabled."""
    return self.config is not None and self.config.enabled

  def _policy_name(self) -> str:
    """Return the configured chunk policy name."""
    if self.chunk_policy is None:
      return "SentenceChunkPolicy"
    return self.chunk_policy.__class__.__name__

  def _config_snapshot(self) -> dict[str, Any]:
    """Build a chunk-policy config snapshot."""
    if self.chunk_policy is None:
      return {}
    config = getattr(self.chunk_policy, "_config", None)
    if config is None:
      return {}
    if is_dataclass(config):
      return asdict(config)
    if hasattr(config, "__dict__"):
      return dict(config.__dict__)
    return {}

  def start_document(self, document) -> DocumentRunRecorder | None:
    """Create a recorder for one document if needed."""
    if not self.enabled:
      return None
    doc_id = document.document_id
    if doc_id in self._sessions:
      return self._sessions[doc_id]
    recorder = DocumentRunRecorder(
        config=self.config,
        doc_id=doc_id,
        policy_name=self._policy_name(),
        model_name=self.model_name,
        max_char_buffer=self.max_char_buffer,
        config_snapshot=self._config_snapshot(),
        pass_index=self.pass_index,
        writer=self._writer,
    )
    self._sessions[doc_id] = recorder
    return recorder

  def get_session(self, doc_id: str) -> DocumentRunRecorder | None:
    """Return the recorder for one document id."""
    return self._sessions.get(doc_id)

  def close_document(
      self,
      doc_id: str,
      *,
      status: str,
      error_message: str | None = None,
  ) -> Path | None:
    """Close and write one document recorder."""
    session = self._sessions.get(doc_id)
    if session is None:
      return None
    return session.close(status=status, error_message=error_message)

  def close_all_pending(
      self,
      *,
      status: str,
      error_message: str | None = None,
  ) -> list[Path | None]:
    """Close any remaining open sessions."""
    return [
        session.close(status=status, error_message=error_message)
        for session in self._sessions.values()
    ]
