"""Structure-aware chunking policy for markdown-style KEP documents."""

from __future__ import annotations

from collections.abc import Iterator
import re

from langextract import chunking
from langextract.chunk_policies.base import PolicyConfig
from langextract.chunk_policies.default_sentence import SentenceChunkPolicy
from langextract.chunk_policies.utils import token_interval_char_length
from langextract.core import data
from langextract.core import tokenizer as tokenizer_lib
from langextract.runtime_observer import get_current_observer_session
from langextract.structure.models import Container
from langextract.structure.models import ContextRef
from langextract.structure.models import StructuredBlock
from langextract.structure.models import StructuredDocument
from langextract.structure.parser import MarkdownStructureParser


class KEPStructuredChunkPolicy:
  """Builds chunks that align better with markdown document structure."""

  _TOC_HEADING_TEXTS = frozenset({"table of contents", "contents"})
  _TOC_OPEN_MARKERS = ("<!-- toc -->", "<!--toc-->")
  _TOC_CLOSE_MARKERS = ("<!-- /toc -->", "<!--/toc-->")
  _ANCHOR_LINK_RE = re.compile(r"\[[^\]]+\]\(#[-a-z0-9_]+\)", re.IGNORECASE)

  def __init__(
      self,
      config: PolicyConfig | None = None,
      parser: MarkdownStructureParser | None = None,
  ):
    """Initializes the policy with optional config and parser."""
    self._config = config or PolicyConfig()
    self._parser = parser or MarkdownStructureParser()
    self._fallback_policy = SentenceChunkPolicy()

  def iter_chunks(
      self,
      document: data.Document,
      max_char_buffer: int,
      tokenizer_impl: tokenizer_lib.Tokenizer,
  ) -> Iterator[chunking.TextChunk]:
    """Yields structure-aware chunks for a document."""
    structured_document = self._parser.parse(
        document=document,
        tokenizer_impl=tokenizer_impl,
    )
    observer_session = get_current_observer_session()
    if observer_session is not None:
      for block in structured_document.blocks:
        observer_session.record_block(
            block,
            structured_document.source_document.tokenized_text,
        )
    containers = self._build_containers(structured_document)
    yield from self._assemble_chunks(
        structured_document=structured_document,
        containers=containers,
        max_char_buffer=max_char_buffer,
        tokenizer_impl=tokenizer_impl,
    )

  def _build_containers(
      self, structured_document: StructuredDocument
  ) -> list[Container]:
    """Builds chunk assembly containers from structured blocks."""
    containers: list[Container] = []
    toc_block_ids = self._detect_toc_block_ids(structured_document)
    blocks = structured_document.blocks
    cursor = 0
    while cursor < len(blocks):
      block = blocks[cursor]
      if self._should_skip_block(block, toc_block_ids):
        observer_session = get_current_observer_session()
        if observer_session is not None:
          observer_session.record_skipped_block(
              block,
              self._skip_reason(block, toc_block_ids),
          )
        cursor += 1
        continue

      if block.kind in ("bullet_item", "numbered_item"):
        container, cursor = self._build_list_container(blocks, cursor)
      elif block.kind == "heading":
        container, cursor = self._build_heading_container(
            blocks,
            cursor,
            toc_block_ids=toc_block_ids,
        )
      elif block.kind in ("checklist_item", "code_fence", "table"):
        container = self._create_container(
            kind="isolated",
            blocks=[block],
            container_id=f"container_{len(containers)}",
        )
        cursor += 1
      else:
        container, cursor = self._build_prose_container(blocks, cursor)
      self._record_container(container, structured_document)
      containers.append(container)
    return containers

  def _build_list_container(
      self, blocks: tuple[StructuredBlock, ...], start_index: int
  ) -> tuple[Container, int]:
    """Groups consecutive list items into one list container."""
    start_block = blocks[start_index]
    grouped = [start_block]
    end_index = start_index + 1
    while end_index < len(blocks):
      block = blocks[end_index]
      if block.kind not in ("bullet_item", "numbered_item"):
        break
      if block.heading_path_block_ids != start_block.heading_path_block_ids:
        break
      grouped.append(block)
      end_index += 1
    return (
        self._create_container(
            kind="list",
            blocks=grouped,
            container_id=f"container_{start_index}",
        ),
        end_index,
    )

  def _build_heading_container(
      self,
      blocks: tuple[StructuredBlock, ...],
      start_index: int,
      toc_block_ids: set[str] | None = None,
  ) -> tuple[Container, int]:
    """Groups a heading with its immediate local body when appropriate."""
    start_block = blocks[start_index]
    grouped = [start_block]
    end_index = start_index + 1
    while end_index < len(blocks):
      block = blocks[end_index]
      if block.kind == "heading":
        break
      if (
          block.heading_path_block_ids
          and block.heading_path_block_ids[-1] != start_block.block_id
      ):
        break
      if not block.heading_path_block_ids and block.kind != "paragraph":
        break
      if self._should_skip_block(block, toc_block_ids):
        end_index += 1
        continue
      grouped.append(block)
      end_index += 1
    title_text = str(start_block.metadata.get("raw_text", ""))
    kind = "qa" if title_text.rstrip().endswith("?") else "subtree"
    return (
        self._create_container(
            kind=kind,
            blocks=grouped,
            container_id=f"container_{start_index}",
            context_block_ids=start_block.heading_path_block_ids,
        ),
        max(end_index, start_index + 1),
    )

  def _build_prose_container(
      self, blocks: tuple[StructuredBlock, ...], start_index: int
  ) -> tuple[Container, int]:
    """Groups adjacent prose-like blocks into a prose container."""
    start_block = blocks[start_index]
    grouped = [start_block]
    end_index = start_index + 1
    while end_index < len(blocks):
      block = blocks[end_index]
      if block.kind not in ("paragraph", "blockquote"):
        break
      if block.heading_path_block_ids != start_block.heading_path_block_ids:
        break
      grouped.append(block)
      end_index += 1
    return (
        self._create_container(
            kind="prose",
            blocks=grouped,
            container_id=f"container_{start_index}",
            context_block_ids=start_block.heading_path_block_ids,
        ),
        end_index,
    )

  def _create_container(
      self,
      kind: str,
      blocks: list[StructuredBlock],
      container_id: str,
      context_block_ids: tuple[str, ...] = (),
  ) -> Container:
    """Creates a container spanning a consecutive set of blocks."""
    return Container(
        container_id=container_id,
        kind=kind,
        block_ids=tuple(block.block_id for block in blocks),
        token_interval=tokenizer_lib.TokenInterval(
            start_index=blocks[0].token_interval.start_index,
            end_index=blocks[-1].token_interval.end_index,
        ),
        context_block_ids=context_block_ids,
    )

  def _record_container(
      self,
      container: Container,
      structured_document: StructuredDocument,
  ) -> None:
    """Record one container when runtime observation is enabled."""
    observer_session = get_current_observer_session()
    if observer_session is not None:
      observer_session.record_container(container, structured_document)

  def _assemble_chunks(
      self,
      structured_document: StructuredDocument,
      containers: list[Container],
      max_char_buffer: int,
      tokenizer_impl: tokenizer_lib.Tokenizer,
  ) -> Iterator[chunking.TextChunk]:
    """Assembles chunk-sized groups from containers."""
    current: list[Container] = []
    current_length = 0
    current_types: set[str] = set()
    tokenized_text = structured_document.source_document.tokenized_text

    for container in containers:
      container_length = token_interval_char_length(
          tokenized_text,
          container.token_interval,
      )
      if container_length > max_char_buffer:
        self._record_chunk_decision(
            current=current,
            candidate=container,
            current_length=current_length,
            candidate_length=container_length,
            merged_length=container_length,
            max_char_buffer=max_char_buffer,
            decision="fallback",
            max_containers_per_chunk=self._config.max_containers_per_chunk,
            max_container_types_per_chunk=(
                self._config.max_container_types_per_chunk
            ),
        )
        if current:
          yield self._merge_containers(
              structured_document,
              current,
          )
          current = []
          current_length = 0
          current_types = set()
        yield from self._fallback_split_large_container(
            structured_document,
            container,
            max_char_buffer,
            tokenizer_impl,
        )
        continue

      if not current:
        current = [container]
        current_length = container_length
        current_types = {container.kind}
        continue

      next_types = current_types | {container.kind}
      merged_length = token_interval_char_length(
          tokenized_text,
          tokenizer_lib.TokenInterval(
              start_index=current[0].token_interval.start_index,
              end_index=container.token_interval.end_index,
          ),
      )
      should_merge = (
          merged_length <= max_char_buffer
          and len(current) < self._config.max_containers_per_chunk
          and len(next_types) <= self._config.max_container_types_per_chunk
          and (
              current_length < max_char_buffer * self._config.min_fill_ratio
              or merged_length
              <= max_char_buffer * self._config.preferred_fill_ratio
          )
      )
      self._record_chunk_decision(
          current=current,
          candidate=container,
          current_length=current_length,
          candidate_length=container_length,
          merged_length=merged_length,
          max_char_buffer=max_char_buffer,
          decision="merge" if should_merge else "flush",
          max_containers_per_chunk=self._config.max_containers_per_chunk,
          max_container_types_per_chunk=(
              self._config.max_container_types_per_chunk
          ),
      )
      if should_merge:
        current.append(container)
        current_length = merged_length
        current_types = next_types
        continue

      yield self._merge_containers(structured_document, current)
      current = [container]
      current_length = container_length
      current_types = {container.kind}

    if current:
      yield self._merge_containers(structured_document, current)

  def _merge_containers(
      self,
      structured_document: StructuredDocument,
      containers: list[Container],
  ) -> chunking.TextChunk:
    """Merges consecutive containers into one text chunk."""
    text_chunk = chunking.TextChunk(
        token_interval=tokenizer_lib.TokenInterval(
            start_index=containers[0].token_interval.start_index,
            end_index=containers[-1].token_interval.end_index,
        ),
        document=structured_document.source_document,
        context_refs=self._build_context_refs(structured_document, containers),
    )
    observer_session = get_current_observer_session()
    if observer_session is not None:
      observer_session.record_chunk(
          text_chunk,
          container_ids=[container.container_id for container in containers],
      )
    return text_chunk

  def _fallback_split_large_container(
      self,
      structured_document: StructuredDocument,
      container: Container,
      max_char_buffer: int,
      tokenizer_impl: tokenizer_lib.Tokenizer,
  ) -> Iterator[chunking.TextChunk]:
    """Falls back to the legacy sentence chunker for oversized containers."""
    document = structured_document.source_document
    sub_text = chunking.get_token_interval_text(
        document.tokenized_text,
        container.token_interval,
    )
    sub_document = data.Document(text=sub_text, document_id=document.document_id)
    sub_document.tokenized_text = tokenizer_impl.tokenize(sub_text)
    base_start = container.token_interval.start_index
    for sub_chunk in self._fallback_policy.iter_chunks(
        document=sub_document,
        max_char_buffer=max_char_buffer,
        tokenizer_impl=tokenizer_impl,
    ):
      text_chunk = chunking.TextChunk(
          token_interval=tokenizer_lib.TokenInterval(
              start_index=base_start + sub_chunk.token_interval.start_index,
              end_index=base_start + sub_chunk.token_interval.end_index,
          ),
          document=document,
          context_refs=self._build_context_refs_for_block_ids(
              structured_document=structured_document,
              context_block_ids=container.context_block_ids,
          ),
      )
      observer_session = get_current_observer_session()
      if observer_session is not None:
        observer_session.record_chunk(
            text_chunk,
            container_ids=[container.container_id],
            fallback_from_container_id=container.container_id,
        )
      yield text_chunk

  def _should_skip_block(
      self,
      block: StructuredBlock,
      toc_block_ids: set[str] | None = None,
  ) -> bool:
    """Returns whether the block should be excluded entirely."""
    return bool(
        self._is_document_title_block(block)
        or (
            toc_block_ids is not None
            and block.block_id in toc_block_ids
            and self._config.skip_toc
        )
        or (block.kind == "checklist_item" and self._config.skip_checklist)
        or (block.kind == "code_fence" and self._config.skip_code_fence)
        or (block.kind == "table" and self._config.skip_table)
    )

  def _skip_reason(
      self,
      block: StructuredBlock,
      toc_block_ids: set[str] | None = None,
  ) -> str:
    """Return a stable skip reason for a skipped block."""
    if self._is_document_title_block(block):
      return "skip_document_title"
    if (
        toc_block_ids is not None
        and block.block_id in toc_block_ids
        and self._config.skip_toc
    ):
      return "skip_toc"
    if block.kind == "checklist_item" and self._config.skip_checklist:
      return "skip_checklist"
    if block.kind == "code_fence" and self._config.skip_code_fence:
      return "skip_code_fence"
    if block.kind == "table" and self._config.skip_table:
      return "skip_table"
    return "skip_block"

  def _detect_toc_block_ids(
      self,
      structured_document: StructuredDocument,
  ) -> set[str]:
    """Detect document-leading table-of-contents blocks."""
    if not self._config.skip_toc:
      return set()

    blocks = structured_document.blocks
    if not blocks:
      return set()

    toc_start_index = None
    explicit_marker_mode = False

    for index, block in enumerate(blocks[:20]):
      raw_text = self._get_block_text(block).strip()
      if (
          block.kind == "heading"
          and block.heading_level == 2
          and self._is_toc_heading_text(raw_text)
      ):
        toc_start_index = index
        break
      if raw_text.lower() in self._TOC_OPEN_MARKERS:
        toc_start_index = index
        explicit_marker_mode = True
        break

    if toc_start_index is None:
      return set()

    toc_block_ids: set[str] = set()
    for index in range(toc_start_index, len(blocks)):
      block = blocks[index]
      raw_text = self._get_block_text(block).strip()
      normalized = raw_text.lower()

      if block.kind == "heading" and index > toc_start_index:
        break

      if normalized in self._TOC_CLOSE_MARKERS:
        toc_block_ids.add(block.block_id)
        break

      if index == toc_start_index:
        toc_block_ids.add(block.block_id)
        continue

      if normalized in self._TOC_OPEN_MARKERS:
        toc_block_ids.add(block.block_id)
        explicit_marker_mode = True
        continue

      if self._is_toc_list_block(block, raw_text):
        toc_block_ids.add(block.block_id)
        continue

      if explicit_marker_mode and block.kind == "paragraph":
        # Allow HTML comment marker paragraphs inside explicit toc sections.
        if normalized.startswith("<!--") and normalized.endswith("-->"):
          toc_block_ids.add(block.block_id)
          continue

      # Once the toc region starts, the first non-toc content ends it.
      break

    if not any(
        self._is_toc_list_block(blocks[i], self._get_block_text(blocks[i]))
        for i, block in enumerate(blocks)
        if block.block_id in toc_block_ids
    ):
      return set()
    return toc_block_ids

  def _get_block_text(self, block: StructuredBlock) -> str:
    """Return normalized source text for one block."""
    return str(block.metadata.get("raw_text", ""))

  def _is_document_title_block(self, block: StructuredBlock) -> bool:
    """Return whether one block is the top-level document title."""
    return block.kind == "heading" and block.heading_level == 1

  def _is_toc_heading_text(self, text: str) -> bool:
    """Return whether one heading text indicates a table of contents."""
    normalized = text.lstrip("#").strip().lower()
    return normalized in self._TOC_HEADING_TEXTS

  def _is_toc_list_block(self, block: StructuredBlock, raw_text: str) -> bool:
    """Return whether one block looks like a TOC entry."""
    if block.kind not in ("bullet_item", "numbered_item"):
      return False
    anchor_links = self._ANCHOR_LINK_RE.findall(raw_text)
    if not anchor_links:
      return False
    line_count = sum(1 for line in raw_text.splitlines() if line.strip())
    return len(anchor_links) >= max(1, line_count)

  def _record_chunk_decision(
      self,
      *,
      current: list[Container],
      candidate: Container,
      current_length: int,
      candidate_length: int,
      merged_length: int,
      max_char_buffer: int,
      decision: str,
      max_containers_per_chunk: int,
      max_container_types_per_chunk: int,
  ) -> None:
    """Record one chunk assembly decision."""
    observer_session = get_current_observer_session()
    if observer_session is None:
      return
    current_types = {container.kind for container in current}
    next_types = current_types | {candidate.kind}
    observer_session.record_chunk_decision(
        candidate_container_id=candidate.container_id,
        current_container_ids=[container.container_id for container in current],
        current_length=current_length,
        candidate_length=candidate_length,
        merged_length=merged_length,
        within_max_char_buffer=merged_length <= max_char_buffer,
        within_max_containers=(
            len(current) < max_containers_per_chunk if current else True
        ),
        within_max_container_types=(
            len(next_types) <= max_container_types_per_chunk
        ),
        current_fill_ratio=(
            current_length / max_char_buffer if max_char_buffer else None
        ),
        decision=decision,
    )

  def _build_context_refs(
      self,
      structured_document: StructuredDocument,
      containers: list[Container],
  ) -> tuple[ContextRef, ...]:
    """Builds context refs for a merged chunk."""
    context_refs: list[ContextRef] = []
    seen = set()
    for container in containers:
      for context_ref in self._build_context_refs_for_block_ids(
          structured_document=structured_document,
          context_block_ids=container.context_block_ids,
      ):
        if context_ref.block_ids in seen:
          continue
        seen.add(context_ref.block_ids)
        context_refs.append(context_ref)
    return tuple(context_refs)

  def _build_context_refs_for_block_ids(
      self,
      context_block_ids: tuple[str, ...],
      structured_document: StructuredDocument | None = None,
  ) -> tuple[ContextRef, ...]:
    """Builds heading-path context refs from block ids."""
    if not structured_document or not context_block_ids:
      return ()

    heading_lines: list[str] = []
    for block_id in context_block_ids:
      block_index = structured_document.block_index.get(block_id)
      if block_index is None:
        continue
      block = structured_document.blocks[block_index]
      raw_text = str(block.metadata.get("raw_text", "")).strip()
      if raw_text:
        heading_lines.append(raw_text)

    if not heading_lines:
      return ()

    return (
        ContextRef(
            ref_type="heading_path",
            block_ids=context_block_ids,
            context_text="\n".join(heading_lines),
        ),
    )
