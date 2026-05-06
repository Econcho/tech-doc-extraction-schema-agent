from __future__ import annotations

import enum
import json
from pathlib import Path
from typing import Any

from langextract.core.data import CharInterval
from residual_info_agents.domain.static.residual_block import ResidualBlock
from residual_info_agents.domain.static.residual_info import ResidualInfo


class ContextLevel(str, enum.Enum):
  SMALL = "small"
  MEDIUM = "medium"
  LARGE = "large"


CONTEXT_LEVEL_SIZES = {
    ContextLevel.SMALL.value: 100,
    ContextLevel.MEDIUM.value: 200,
    ContextLevel.LARGE.value: 300,
}


def parse_context_level(context_level: ContextLevel | str) -> int:
  value = (
      context_level.value
      if isinstance(context_level, enum.Enum)
      else str(context_level)
  )
  if value not in CONTEXT_LEVEL_SIZES:
    raise ValueError(f"Unsupported context level: {context_level}")
  return CONTEXT_LEVEL_SIZES[value]


def load_residual_info(ref: ResidualInfo | dict[str, Any] | Path | str) -> ResidualInfo:
  if isinstance(ref, ResidualInfo):
    return ref
  if isinstance(ref, (str, Path)):
    data = json.loads(Path(ref).read_text(encoding="utf-8"))
    return load_residual_info(data)
  if isinstance(ref, dict):
    blocks_data = ref.get("resblocks", ref.get("blocks", []))
    return ResidualInfo(
        original_doc_ref=ref.get("original_doc_ref", ref.get("original_doc")),
        extraction_doc_ref=ref.get("extraction_doc_ref", ref.get("extraction_doc")),
        resblocks=[residual_block_from_dict(item) for item in blocks_data],
    )
  raise TypeError(f"Unsupported residual info reference: {type(ref)!r}")


def residual_block_from_dict(data: dict[str, Any]) -> ResidualBlock:
  char_interval = data.get("char_interval")
  interval = None
  if isinstance(char_interval, dict):
    interval = CharInterval(
        start_pos=char_interval.get("start_pos"),
        end_pos=char_interval.get("end_pos"),
    )
  return ResidualBlock(
      text=str(data.get("text", "")),
      block_id=data.get("block_id"),
      char_interval=interval,
      heading_tree=list(data.get("heading_tree", [])),
  )


def get_blocks_by_id(
    residual_info: ResidualInfo, resblock_ids: list[int]
) -> list[ResidualBlock]:
  blocks_by_id = {
      block.block_id: block
      for block in residual_info.resblocks
      if block.block_id is not None
  }
  missing_ids = [block_id for block_id in resblock_ids if block_id not in blocks_by_id]
  if missing_ids:
    raise ValueError(f"Unknown residual block ids: {missing_ids}")
  return [blocks_by_id[block_id] for block_id in resblock_ids]


def get_blocks_from_resblocks_data(
    resblocks: list[dict[str, Any]],
    resblock_ids: list[int],
) -> list[ResidualBlock]:
  blocks_by_id = {
      block.block_id: block
      for block in (residual_block_from_dict(item) for item in resblocks)
      if block.block_id is not None
  }
  missing_ids = [block_id for block_id in resblock_ids if block_id not in blocks_by_id]
  if missing_ids:
    raise ValueError(f"Unknown residual block ids: {missing_ids}")
  return [blocks_by_id[block_id] for block_id in resblock_ids]


def get_block_interval(block: ResidualBlock) -> CharInterval:
  if block.char_interval is None:
    raise ValueError(f"Residual block {block.block_id} has no char_interval.")
  if block.char_interval.start_pos is None or block.char_interval.end_pos is None:
    raise ValueError(f"Residual block {block.block_id} has an incomplete interval.")
  return block.char_interval


def resolve_doc_path(value: Path | str | None, *, name: str) -> Path:
  if value is None:
    raise ValueError(f"{name} is missing.")
  return Path(value)


def remove_intervals_from_slice(
    text_slice: str,
    slice_start: int,
    intervals: list[CharInterval],
) -> str:
  pieces: list[str] = []
  cursor = slice_start
  slice_end = slice_start + len(text_slice)
  for interval in intervals:
    if interval.start_pos is None or interval.end_pos is None:
      continue
    start_pos = max(interval.start_pos, slice_start)
    end_pos = min(interval.end_pos, slice_end)
    if start_pos >= end_pos:
      continue
    if cursor < start_pos:
      pieces.append(text_slice[cursor - slice_start:start_pos - slice_start])
    cursor = max(cursor, end_pos)
  if cursor < slice_end:
    pieces.append(text_slice[cursor - slice_start:])
  return "".join(pieces)
