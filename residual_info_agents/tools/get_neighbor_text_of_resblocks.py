from __future__ import annotations

from pathlib import Path

from residual_info_agents.domain.static.residual_info import ResidualInfo
from residual_info_agents.domain.tools.context_block import ContextBlock
from residual_info_agents.tools._common import ContextLevel
from residual_info_agents.tools._common import get_block_interval
from residual_info_agents.tools._common import get_blocks_from_resblocks_data
from residual_info_agents.tools._common import parse_context_level
from residual_info_agents.tools._common import remove_intervals_from_slice
from residual_info_agents.tools._common import resolve_doc_path


def get_neighbor_text_of_resblocks(
    doc_ref,
    resblocks: list[dict],
    resblock_ids: list[int],
    context_levels: list[ContextLevel | str],
    ignore_code_fence: bool = False,
) -> list[ContextBlock]:
  if len(resblock_ids) != len(context_levels):
    raise ValueError("resblock_ids and context_levels must have the same length.")

  doc_path = resolve_doc_path(doc_ref, name="doc_ref")
  original_text = Path(doc_path).read_text(encoding="utf-8")
  code_fence_intervals = (
      ResidualInfo._collect_code_fence_intervals(original_text)
      if ignore_code_fence
      else []
  )

  blocks = get_blocks_from_resblocks_data(resblocks, resblock_ids)
  outputs: list[ContextBlock] = []
  for block, context_level in zip(blocks, context_levels):
    interval = get_block_interval(block)
    context_size = parse_context_level(context_level)
    previous_start = max(0, interval.start_pos - context_size)
    previous_text = original_text[previous_start:interval.start_pos]
    next_end = min(len(original_text), interval.end_pos + context_size)
    next_text = original_text[interval.end_pos:next_end]

    if ignore_code_fence:
      previous_text = remove_intervals_from_slice(
          previous_text, previous_start, code_fence_intervals
      )
      next_text = remove_intervals_from_slice(
          next_text, interval.end_pos, code_fence_intervals
      )

    outputs.append(
        ContextBlock(
            resblock_id=block.block_id,
            resblock_text=block.text,
            previous_neighbor_text=previous_text,
            next_neighbor_text=next_text,
        )
    )
  return outputs
