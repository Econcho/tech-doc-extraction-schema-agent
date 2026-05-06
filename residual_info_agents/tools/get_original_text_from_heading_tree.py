from __future__ import annotations

import re
from pathlib import Path

from residual_info_agents.domain.tools.full_heading_context import (
    FullHeadingContext,
)
from residual_info_agents.domain.static.residual_info import ResidualInfo
from residual_info_agents.tools._common import get_blocks_from_resblocks_data
from residual_info_agents.tools._common import remove_intervals_from_slice
from residual_info_agents.tools._common import resolve_doc_path


def _iter_heading_lines(original_text: str) -> list[tuple[int, int, int, str]]:
  headings: list[tuple[int, int, int, str]] = []
  cursor = 0
  in_code_fence = False
  current_fence_marker: str | None = None
  for line in original_text.splitlines(keepends=True):
    fence_marker = ResidualInfo._is_code_fence_line(line)
    if fence_marker is not None:
      if not in_code_fence:
        in_code_fence = True
        current_fence_marker = fence_marker
      elif fence_marker == current_fence_marker:
        in_code_fence = False
        current_fence_marker = None
      cursor += len(line)
      continue

    if not in_code_fence:
      match = re.match(r"^(#{1,6})\s+.+?\s*$", line.lstrip())
      if match:
        headings.append((cursor, cursor + len(line), len(match.group(1)), line.strip()))
    cursor += len(line)
  return headings


def _find_heading_content(
    original_text: str,
    heading_tree: list[str],
) -> str:
  if not heading_tree:
    return original_text

  target_heading = heading_tree[-1].strip()
  headings = _iter_heading_lines(original_text)
  for index, (start_pos, end_pos, level, heading_text) in enumerate(headings):
    if heading_text != target_heading:
      continue
    section_end = len(original_text)
    for next_start, _, next_level, _ in headings[index + 1:]:
      if next_level <= level:
        section_end = next_start
        break

    content_parts: list[str] = []
    cursor = end_pos
    for child_start, child_end, child_level, _ in headings[index + 1:]:
      if child_start >= section_end:
        break
      if child_level <= level:
        break
      if cursor < child_start:
        content_parts.append(original_text[cursor:child_start])
      content_parts.append(original_text[child_start:child_end])
      next_sibling_or_parent = section_end
      for following_start, _, following_level, _ in headings:
        if following_start <= child_start:
          continue
        if following_level <= child_level:
          next_sibling_or_parent = min(next_sibling_or_parent, following_start)
          break
      cursor = max(cursor, next_sibling_or_parent)
    if cursor < section_end:
      content_parts.append(original_text[cursor:section_end])
    return "".join(content_parts).strip()

  raise ValueError(f"Heading not found: {target_heading}")


def get_original_text_from_heading_tree(
    doc_ref,
    resblocks: list[dict],
    resblock_ids: list[int],
    ignore_code_fence: bool = False,
) -> list[FullHeadingContext]:
  doc_path = resolve_doc_path(doc_ref, name="doc_ref")
  original_text = Path(doc_path).read_text(encoding="utf-8")
  code_fence_intervals = (
      ResidualInfo._collect_code_fence_intervals(original_text)
      if ignore_code_fence
      else []
  )

  outputs: list[FullHeadingContext] = []
  for block in get_blocks_from_resblocks_data(resblocks, resblock_ids):
    content = _find_heading_content(original_text, block.heading_tree)
    if ignore_code_fence:
      content_start = original_text.find(content)
      if content_start >= 0:
        content = remove_intervals_from_slice(
            content, content_start, code_fence_intervals
        )
    outputs.append(
        FullHeadingContext(
            heading_tree=block.heading_tree,
            content=content,
        )
    )
  return outputs
