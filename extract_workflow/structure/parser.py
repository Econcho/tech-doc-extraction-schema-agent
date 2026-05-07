"""Markdown parser used by structure-aware chunk policies."""

from __future__ import annotations

from dataclasses import dataclass
import re

from langextract.core import data
from langextract.core import tokenizer as tokenizer_lib
from langextract.structure.char_token_map import CharTokenMap
from langextract.structure.models import StructuredBlock
from langextract.structure.models import StructuredDocument

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHECKLIST_RE = re.compile(r"^(\s*)[-*+]\s+\[(?: |x|X)\]\s+")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+")
_NUMBERED_RE = re.compile(r"^(\s*)\d+[.)]\s+")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")


@dataclass(slots=True)
class _Line:
  """A source line with character offsets."""

  text: str
  start_pos: int
  end_pos: int


@dataclass(slots=True)
class _BlockCandidate:
  """An intermediate parser block before token alignment."""

  kind: str
  start_pos: int
  end_pos: int
  heading_level: int | None = None
  parent_block_id: str | None = None
  list_level: int = 0
  indent: int = 0
  metadata: dict[str, object] | None = None


class MarkdownStructureParser:
  """Parses markdown-ish text into structure blocks."""

  def parse(
      self,
      document: data.Document,
      tokenizer_impl: tokenizer_lib.Tokenizer | None = None,
  ) -> StructuredDocument:
    """Parses a document into a structured representation."""
    if tokenizer_impl is not None:
      document.tokenized_text = tokenizer_impl.tokenize(document.text or "")
    tokenized_text = document.tokenized_text
    char_map = CharTokenMap.from_tokenized_text(tokenized_text)
    lines = self._split_lines(tokenized_text.text)

    blocks: list[StructuredBlock] = []
    block_index: dict[str, int] = {}
    heading_children: dict[str, list[str]] = {}
    heading_stack: list[tuple[int, str]] = []

    candidate_index = 0
    cursor = 0
    while cursor < len(lines):
      line = lines[cursor]
      if not line.text.strip():
        cursor += 1
        continue

      candidate, cursor = self._parse_candidate(lines, cursor)
      token_interval = char_map.char_span_to_token_interval(
          candidate.start_pos,
          candidate.end_pos,
      )
      if token_interval is None:
        continue

      if candidate.kind == "heading":
        while heading_stack and heading_stack[-1][0] >= candidate.heading_level:
          heading_stack.pop()
      heading_path = tuple(block_id for _, block_id in heading_stack)

      block_id = f"block_{candidate_index}"
      candidate_index += 1
      structured_block = StructuredBlock(
          block_id=block_id,
          token_interval=token_interval,
          kind=candidate.kind,
          heading_level=candidate.heading_level,
          heading_path_block_ids=heading_path,
          parent_block_id=candidate.parent_block_id,
          list_level=candidate.list_level,
          indent=candidate.indent,
          metadata=candidate.metadata or {},
      )
      block_index[block_id] = len(blocks)
      blocks.append(structured_block)

      if candidate.kind == "heading":
        if heading_stack:
          parent_heading_id = heading_stack[-1][1]
          heading_children.setdefault(parent_heading_id, []).append(block_id)
        heading_stack.append((candidate.heading_level or 0, block_id))

    return StructuredDocument(
        source_document=document,
        blocks=tuple(blocks),
        block_index=block_index,
        heading_children={
            block_id: tuple(children)
            for block_id, children in heading_children.items()
        },
    )

  def _split_lines(self, text: str) -> list[_Line]:
    """Splits text into lines while preserving source offsets."""
    lines: list[_Line] = []
    cursor = 0
    for raw_line in text.splitlines(keepends=True):
      start_pos = cursor
      cursor += len(raw_line)
      lines.append(_Line(text=raw_line, start_pos=start_pos, end_pos=cursor))
    return lines

  def _parse_candidate(
      self,
      lines: list[_Line],
      start_index: int,
  ) -> tuple[_BlockCandidate, int]:
    """Parses one structure block starting at a line index."""
    line = lines[start_index]
    text = line.text
    heading_match = _HEADING_RE.match(text)
    if heading_match:
      level = len(heading_match.group(1))
      return (
          _BlockCandidate(
              kind="heading",
              start_pos=line.start_pos,
              end_pos=line.end_pos,
              heading_level=level,
              metadata={"raw_text": text.rstrip("\r\n")},
          ),
          start_index + 1,
      )

    if _FENCE_RE.match(text):
      return self._parse_code_fence(lines, start_index)
    if self._is_table_line(text):
      return self._parse_table(lines, start_index)
    if _CHECKLIST_RE.match(text):
      return self._parse_repeated_block(
          lines, start_index, "checklist_item", _CHECKLIST_RE
      )
    if _NUMBERED_RE.match(text):
      return self._parse_repeated_block(
          lines, start_index, "numbered_item", _NUMBERED_RE
      )
    if _BULLET_RE.match(text):
      return self._parse_repeated_block(
          lines, start_index, "bullet_item", _BULLET_RE
      )
    if _BLOCKQUOTE_RE.match(text):
      return self._parse_prefixed_block(lines, start_index, "blockquote")
    return self._parse_paragraph(lines, start_index)

  def _parse_code_fence(
      self, lines: list[_Line], start_index: int
  ) -> tuple[_BlockCandidate, int]:
    """Parses a fenced code block."""
    opening = _FENCE_RE.match(lines[start_index].text)
    fence_marker = opening.group(1) if opening else "```"
    fence_char = fence_marker[0]
    end_index = start_index + 1
    while end_index < len(lines):
      if re.match(rf"^\s*{re.escape(fence_char)}{{3,}}", lines[end_index].text):
        end_index += 1
        break
      end_index += 1
    return (
        _BlockCandidate(
            kind="code_fence",
            start_pos=lines[start_index].start_pos,
            end_pos=lines[end_index - 1].end_pos,
            metadata={
                "raw_text": "".join(
                    line.text for line in lines[start_index:end_index]
                )
            },
        ),
        end_index,
    )

  def _parse_table(
      self, lines: list[_Line], start_index: int
  ) -> tuple[_BlockCandidate, int]:
    """Parses consecutive table rows as one block."""
    end_index = start_index + 1
    while end_index < len(lines):
      if not self._is_table_line(lines[end_index].text):
        break
      end_index += 1
    return (
        _BlockCandidate(
            kind="table",
            start_pos=lines[start_index].start_pos,
            end_pos=lines[end_index - 1].end_pos,
            metadata={
                "raw_text": "".join(
                    line.text for line in lines[start_index:end_index]
                )
            },
        ),
        end_index,
    )

  def _parse_repeated_block(
      self,
      lines: list[_Line],
      start_index: int,
      kind: str,
      pattern: re.Pattern[str],
  ) -> tuple[_BlockCandidate, int]:
    """Parses a single list-like block item with continuation lines."""
    match = pattern.match(lines[start_index].text)
    indent = len(match.group(1)) if match else 0
    list_level = indent // 2
    end_index = start_index + 1
    while end_index < len(lines):
      next_line = lines[end_index]
      if not next_line.text.strip():
        break
      if self._starts_special_block(next_line.text):
        break
      if len(next_line.text) - len(next_line.text.lstrip(" ")) <= indent:
        break
      end_index += 1
    return (
        _BlockCandidate(
            kind=kind,
            start_pos=lines[start_index].start_pos,
            end_pos=lines[end_index - 1].end_pos,
            list_level=list_level,
            indent=indent,
            metadata={
                "raw_text": "".join(
                    line.text for line in lines[start_index:end_index]
                )
            },
        ),
        end_index,
    )

  def _parse_prefixed_block(
      self,
      lines: list[_Line],
      start_index: int,
      kind: str,
  ) -> tuple[_BlockCandidate, int]:
    """Parses consecutive quoted lines as one block."""
    end_index = start_index + 1
    while end_index < len(lines):
      next_line = lines[end_index]
      if not next_line.text.strip():
        break
      if not _BLOCKQUOTE_RE.match(next_line.text):
        break
      end_index += 1
    return (
        _BlockCandidate(
            kind=kind,
            start_pos=lines[start_index].start_pos,
            end_pos=lines[end_index - 1].end_pos,
            metadata={
                "raw_text": "".join(
                    line.text for line in lines[start_index:end_index]
                )
            },
        ),
        end_index,
    )

  def _parse_paragraph(
      self, lines: list[_Line], start_index: int
  ) -> tuple[_BlockCandidate, int]:
    """Parses a paragraph block."""
    end_index = start_index + 1
    while end_index < len(lines):
      next_line = lines[end_index]
      if not next_line.text.strip():
        break
      if self._starts_special_block(next_line.text):
        break
      end_index += 1
    return (
        _BlockCandidate(
            kind="paragraph",
            start_pos=lines[start_index].start_pos,
            end_pos=lines[end_index - 1].end_pos,
            metadata={
                "raw_text": "".join(
                    line.text for line in lines[start_index:end_index]
                )
            },
        ),
        end_index,
    )

  def _is_table_line(self, text: str) -> bool:
    """Returns whether a line looks like a markdown table row."""
    stripped = text.strip()
    return stripped.count("|") >= 2 and not _BLOCKQUOTE_RE.match(text)

  def _starts_special_block(self, text: str) -> bool:
    """Returns whether a line begins a non-paragraph block."""
    return bool(
        _HEADING_RE.match(text)
        or _FENCE_RE.match(text)
        or _CHECKLIST_RE.match(text)
        or _NUMBERED_RE.match(text)
        or _BULLET_RE.match(text)
        or _BLOCKQUOTE_RE.match(text)
        or self._is_table_line(text)
    )
