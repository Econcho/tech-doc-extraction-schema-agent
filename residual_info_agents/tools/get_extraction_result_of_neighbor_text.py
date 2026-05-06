from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langextract.core.data import CharInterval
from residual_info_agents.domain.tools.neighbor_extractions import (
    NeighborExtractions,
)
from residual_info_agents.domain.tools.neighbor_extractions import (
    SimplifiedExtraction,
)
from residual_info_agents.tools._common import ContextLevel
from residual_info_agents.tools._common import get_block_interval
from residual_info_agents.tools._common import get_blocks_from_resblocks_data
from residual_info_agents.tools._common import parse_context_level
from residual_info_agents.tools._common import resolve_doc_path


def _collect_extractions(obj: Any) -> list[SimplifiedExtraction]:
  extractions: list[SimplifiedExtraction] = []
  if isinstance(obj, dict):
    char_interval = obj.get("char_interval")
    if isinstance(char_interval, dict) and "extraction_class" in obj:
      start_pos = char_interval.get("start_pos")
      end_pos = char_interval.get("end_pos")
      if isinstance(start_pos, int) and isinstance(end_pos, int):
        extractions.append(
            SimplifiedExtraction(
                extraction_class=str(obj.get("extraction_class", "")),
                extraction_text=str(obj.get("extraction_text", "")),
                char_interval=CharInterval(start_pos=start_pos, end_pos=end_pos),
                attributes=obj.get("attributes"),
            )
        )
    for value in obj.values():
      extractions.extend(_collect_extractions(value))
  elif isinstance(obj, list):
    for item in obj:
      extractions.extend(_collect_extractions(item))
  return extractions


def get_extraction_result_of_neighbor_text(
    extraction_doc_ref,
    resblocks: list[dict],
    resblock_ids: list[int],
    context_levels: list[ContextLevel | str],
) -> list[NeighborExtractions]:
  if len(resblock_ids) != len(context_levels):
    raise ValueError("resblock_ids and context_levels must have the same length.")

  extraction_path = resolve_doc_path(extraction_doc_ref, name="extraction_doc_ref")
  extraction_data = json.loads(Path(extraction_path).read_text(encoding="utf-8"))
  extractions = _collect_extractions(extraction_data)

  outputs: list[NeighborExtractions] = []
  blocks = get_blocks_from_resblocks_data(resblocks, resblock_ids)
  for block, context_level in zip(blocks, context_levels):
    interval = get_block_interval(block)
    context_size = parse_context_level(context_level)
    query_start = max(0, interval.start_pos - context_size)
    query_end = interval.end_pos + context_size
    neighbor_extractions = [
        extraction
        for extraction in extractions
        if (
            extraction.char_interval.start_pos is not None
            and extraction.char_interval.end_pos is not None
            and extraction.char_interval.start_pos < query_end
            and extraction.char_interval.end_pos > query_start
        )
    ]
    outputs.append(
        NeighborExtractions(
            resblock_id=block.block_id,
            extraction=neighbor_extractions,
        )
    )
  return outputs
