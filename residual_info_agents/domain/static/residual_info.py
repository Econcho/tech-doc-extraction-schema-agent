from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__ in (None, ""):
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from langextract.core.data import CharInterval
from residual_info_agents.domain.static.residual_block import ResidualBlock


@dataclasses.dataclass
class ResidualInfo:
  """Complete cleaned residual blocks persisted as static agent input."""

  original_doc_ref: Path | str
  extraction_doc_ref: Path | str
  resblocks: list[ResidualBlock] = dataclasses.field(default_factory=list)

  @staticmethod
  def _collect_char_intervals(obj: Any) -> list[CharInterval]:
    """Recursively collects all valid `char_interval` objects from JSON data."""

    intervals: list[CharInterval] = []

    if isinstance(obj, dict):
      char_interval = obj.get("char_interval")
      if isinstance(char_interval, dict):
        start_pos = char_interval.get("start_pos")
        end_pos = char_interval.get("end_pos")
        if (
            isinstance(start_pos, int)
            and isinstance(end_pos, int)
            and 0 <= start_pos < end_pos
        ):
          intervals.append(
              CharInterval(start_pos=start_pos, end_pos=end_pos)
          )

      for value in obj.values():
        intervals.extend(ResidualInfo._collect_char_intervals(value))
    elif isinstance(obj, list):
      for item in obj:
        intervals.extend(ResidualInfo._collect_char_intervals(item))

    return intervals

  @staticmethod
  def _collect_char_intervals_with_ignore_class(
      obj: Any, ignore_class: list[str]
  ) -> list[CharInterval]:
    """Collects `char_interval` objects while skipping ignored classes."""

    intervals: list[CharInterval] = []
    ignored_classes = set(ignore_class)

    if isinstance(obj, dict):
      extraction_class = obj.get("extraction_class")
      if extraction_class in ignored_classes:
        return intervals

      char_interval = obj.get("char_interval")
      if isinstance(char_interval, dict):
        start_pos = char_interval.get("start_pos")
        end_pos = char_interval.get("end_pos")
        if (
            isinstance(start_pos, int)
            and isinstance(end_pos, int)
            and 0 <= start_pos < end_pos
        ):
          intervals.append(
              CharInterval(start_pos=start_pos, end_pos=end_pos)
          )

      for value in obj.values():
        intervals.extend(
            ResidualInfo._collect_char_intervals_with_ignore_class(
                value, ignore_class
            )
        )
    elif isinstance(obj, list):
      for item in obj:
        intervals.extend(
            ResidualInfo._collect_char_intervals_with_ignore_class(
                item, ignore_class
            )
        )

    return intervals

  @staticmethod
  def _merge_intervals(
      intervals: list[CharInterval], text_length: int
  ) -> list[CharInterval]:
    """Clamps, sorts, and merges overlapping covered intervals."""

    normalized: list[tuple[int, int]] = []
    for interval in intervals:
      if interval.start_pos is None or interval.end_pos is None:
        continue
      start_pos = max(0, min(interval.start_pos, text_length))
      end_pos = max(0, min(interval.end_pos, text_length))
      if start_pos < end_pos:
        normalized.append((start_pos, end_pos))

    if not normalized:
      return []

    normalized.sort()
    merged: list[list[int]] = [[normalized[0][0], normalized[0][1]]]
    for start_pos, end_pos in normalized[1:]:
      last_start, last_end = merged[-1]
      if start_pos <= last_end:
        merged[-1][1] = max(last_end, end_pos)
      else:
        merged.append([start_pos, end_pos])

    return [
        CharInterval(start_pos=start_pos, end_pos=end_pos)
        for start_pos, end_pos in merged
    ]

  @staticmethod
  def _collect_code_fence_intervals(original_text: str) -> list[CharInterval]:
    """Collects fenced-code-block intervals to optionally exclude them.

    Both triple-backtick and triple-tilde fences are supported. If a fence is
    not closed, the block is treated as running until end of document.
    """

    intervals: list[CharInterval] = []
    fence_start: int | None = None
    fence_marker: str | None = None
    cursor = 0

    for line in original_text.splitlines(keepends=True):
      stripped_line = line.lstrip()
      if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
        current_marker = stripped_line[:3]
        if fence_start is None:
          fence_start = cursor
          fence_marker = current_marker
        elif current_marker == fence_marker:
          intervals.append(
              CharInterval(start_pos=fence_start, end_pos=cursor + len(line))
          )
          fence_start = None
          fence_marker = None
      cursor += len(line)

    if fence_start is not None:
      intervals.append(
          CharInterval(start_pos=fence_start, end_pos=len(original_text))
      )

    return intervals

  @staticmethod
  def _collect_toc_intervals(original_text: str) -> list[CharInterval]:
    """Collects explicit Markdown TOC regions delimited by HTML comments."""

    intervals: list[CharInterval] = []
    toc_pattern = re.compile(r"<!--\s*toc\s*-->.*?<!--\s*/toc\s*-->", re.DOTALL)
    for match in toc_pattern.finditer(original_text):
      intervals.append(
          CharInterval(start_pos=match.start(), end_pos=match.end())
      )
    return intervals

  @staticmethod
  def _is_code_fence_line(line: str) -> str | None:
    """Returns the fence marker for a fence line, otherwise `None`."""

    stripped_line = line.lstrip()
    if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
      return stripped_line[:3]
    return None

  @staticmethod
  def _collect_heading_intervals(original_text: str) -> list[CharInterval]:
    """Collects Markdown heading-line intervals outside code fences.

    These intervals are treated as already covered before residual spans are
    computed, so headings are removed at the interval stage rather than only by
    post-processing.
    """

    heading_intervals: list[CharInterval] = []
    in_code_fence = False
    current_fence_marker: str | None = None
    cursor = 0

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
        stripped_line = line.lstrip()
        if re.match(r"^(#{1,6})\s+.+?\s*$", stripped_line):
          heading_intervals.append(
              CharInterval(start_pos=cursor, end_pos=cursor + len(line))
          )

      cursor += len(line)

    return heading_intervals

  @staticmethod
  def _collect_heading_states(
      original_text: str,
  ) -> list[tuple[int, list[str]]]:
    """Builds heading-tree snapshots keyed by document character position.

    Each tuple is `(heading_start_pos, heading_tree_at_that_point)`. Later
    residual blocks use the latest snapshot before their start position as
    contextual section ancestry.
    """

    heading_states: list[tuple[int, list[str]]] = []
    heading_stack: list[str] = []
    in_code_fence = False
    current_fence_marker: str | None = None
    cursor = 0

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
        stripped_line = line.lstrip()
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped_line)
        if heading_match:
          level = len(heading_match.group(1))
          heading_text = stripped_line.strip()
          heading_stack = heading_stack[: level - 1]
          heading_stack.append(heading_text)
          heading_states.append((cursor, heading_stack.copy()))

      cursor += len(line)

    return heading_states

  @staticmethod
  def _get_heading_tree_for_pos(
      pos: int, heading_states: list[tuple[int, list[str]]]
  ) -> list[str]:
    """Returns the active heading tree for a given document position."""

    heading_tree: list[str] = []
    for heading_pos, current_tree in heading_states:
      if heading_pos > pos:
        break
      heading_tree = current_tree
    return heading_tree.copy()

  @staticmethod
  def _get_residual_intervals(
      covered_intervals: list[CharInterval], text_length: int
  ) -> list[CharInterval]:
    """Computes the complement intervals of already covered text."""

    residual_intervals: list[CharInterval] = []
    cursor = 0

    for interval in covered_intervals:
      if interval.start_pos is None or interval.end_pos is None:
        continue
      if cursor < interval.start_pos:
        residual_intervals.append(
            CharInterval(start_pos=cursor, end_pos=interval.start_pos)
        )
      cursor = max(cursor, interval.end_pos)

    if cursor < text_length:
      residual_intervals.append(
          CharInterval(start_pos=cursor, end_pos=text_length)
      )

    return residual_intervals

  @staticmethod
  def _is_effectively_empty_text(text: str) -> bool:
    """Checks whether text is empty or only low-signal punctuation/markup."""

    stripped_text = text.strip()
    if not stripped_text:
      return True
    return re.fullmatch(r"[\s\-\[\]\(\)#>*_`~|:;,.!?/\\]+", stripped_text) is not None

  @staticmethod
  def _is_url_only_text(text: str) -> bool:
    """Checks whether a block is effectively just a URL with optional wrappers.

    This catches cases such as plain URLs and URLs surrounded by punctuation or
    Markdown delimiters that do not provide useful residual content.
    """

    stripped_text = text.strip()
    if not stripped_text:
      return False
    cleaned_text = re.sub(r"^[\s\[\]\(\)<>{}'\"`*_#.,;:!?-]+", "", stripped_text)
    cleaned_text = re.sub(r"[\s\[\]\(\)<>{}'\"`*_#.,;:!?-]+$", "", cleaned_text)
    if not cleaned_text:
      return False
    return re.fullmatch(r"https?://\S+|www\.\S+", cleaned_text) is not None

  @staticmethod
  def _is_toc_text(text: str) -> bool:
    """Heuristically detects table-of-contents style residual fragments."""

    stripped_text = text.strip()
    if "<!-- toc -->" in stripped_text or "<!-- /toc -->" in stripped_text:
      return True
    toc_link_count = len(re.findall(r"\[[^\]]+\]\(#.+?\)", text))
    if toc_link_count >= 2:
      return True
    return False

  @staticmethod
  def _extract_leading_heading(
      text: str,
  ) -> tuple[str | None, str, int]:
    """Extracts a leading Markdown heading from block text if present.

    Returns:
      A tuple of:
        - heading text including `#` markers, or `None`
        - remaining text after removing the heading chunk
        - removed heading-chunk length in characters
    """

    heading_match = re.match(
        r"^(\s*(#{1,6})\s+[^\n]+(?:\n+|$))",
        text,
    )
    if not heading_match:
      return None, text, 0

    heading_chunk = heading_match.group(1)
    heading_line = heading_chunk.strip()
    remaining_text = text[len(heading_chunk):]
    return heading_line, remaining_text, len(heading_chunk)

  @staticmethod
  def _is_heading_only_text(text: str) -> bool:
    """Checks whether text contains only a heading and no body content."""

    heading_line, remaining_text, _ = ResidualInfo._extract_leading_heading(text)
    if heading_line is None:
      return False
    return not remaining_text.strip()

  @staticmethod
  def _normalize_single_block(
      block: ResidualBlock,
  ) -> ResidualBlock | None:
    """Cleans one residual block and drops it if it is clearly invalid.

    Normalization currently:
    - drops TOC-like fragments
    - drops URL-only fragments
    - drops heading-only fragments
    - trims surrounding whitespace and syncs char_interval accordingly
    - if the block starts with a heading followed by body text, moves that
      heading into `heading_tree` and removes it from `text`
    - drops empty / punctuation-only fragments after cleanup
    """

    if block.char_interval is None:
      return None

    start_pos = block.char_interval.start_pos
    end_pos = block.char_interval.end_pos
    if start_pos is None or end_pos is None:
      return None

    text = block.text
    heading_tree = block.heading_tree.copy()

    if ResidualInfo._is_toc_text(text):
      return None
    if ResidualInfo._is_url_only_text(text):
      return None
    if ResidualInfo._is_heading_only_text(text):
      return None

    leading_ws_len = len(text) - len(text.lstrip())
    trailing_ws_len = len(text) - len(text.rstrip())
    if leading_ws_len:
      text = text[leading_ws_len:]
      start_pos += leading_ws_len
    if trailing_ws_len:
      text = text[: len(text) - trailing_ws_len]
      end_pos -= trailing_ws_len

    if ResidualInfo._is_effectively_empty_text(text):
      return None
    if ResidualInfo._is_url_only_text(text):
      return None

    heading_line, remaining_text, heading_offset = (
        ResidualInfo._extract_leading_heading(text)
    )
    if heading_line is not None:
      if not remaining_text.strip():
        return None
      heading_tree.append(heading_line)
      text = remaining_text
      start_pos += heading_offset

    leading_ws_len = len(text) - len(text.lstrip())
    trailing_ws_len = len(text) - len(text.rstrip())
    if leading_ws_len:
      text = text[leading_ws_len:]
      start_pos += leading_ws_len
    if trailing_ws_len:
      text = text[: len(text) - trailing_ws_len]
      end_pos -= trailing_ws_len

    if start_pos >= end_pos:
      return None
    if ResidualInfo._is_effectively_empty_text(text):
      return None
    if ResidualInfo._is_url_only_text(text):
      return None

    return ResidualBlock(
        block_id=block.block_id,
        char_interval=CharInterval(start_pos=start_pos, end_pos=end_pos),
        text=text,
        heading_tree=heading_tree,
    )

  @staticmethod
  def _normalize_blocks(
      blocks: list[ResidualBlock],
  ) -> list[ResidualBlock]:
    """Applies block normalization and reassigns sequential block ids."""

    normalized_blocks: list[ResidualBlock] = []
    for block in blocks:
      normalized_block = ResidualInfo._normalize_single_block(block)
      if normalized_block is None:
        continue
      normalized_block.block_id = len(normalized_blocks)
      normalized_blocks.append(normalized_block)
    return normalized_blocks

  @staticmethod
  def _build_residual_blocks(
      residual_intervals: list[CharInterval],
      original_text: str,
  ) -> list[ResidualBlock]:
    """Converts raw residual intervals into residual blocks with heading trees."""

    heading_states = ResidualInfo._collect_heading_states(original_text)
    residual_blocks: list[ResidualBlock] = []

    for interval in residual_intervals:
      if interval.start_pos is None or interval.end_pos is None:
        continue
      residual_blocks.append(
          ResidualBlock(
              block_id=-1,
              char_interval=interval,
              text=original_text[interval.start_pos:interval.end_pos],
              heading_tree=ResidualInfo._get_heading_tree_for_pos(
                  interval.start_pos, heading_states
              ),
          )
      )

    return residual_blocks

  @staticmethod
  def _dump_residual_json(
      residual_info: ResidualInfo, output_path: Path
  ) -> None:
    """Serializes residual info to a JSON file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "original_doc_ref": str(residual_info.original_doc_ref),
        "extraction_doc_ref": str(residual_info.extraction_doc_ref),
        "resblocks": [
            {
                "block_id": block.block_id,
                "text": block.text,
                "char_interval": {
                    "start_pos": block.char_interval.start_pos,
                    "end_pos": block.char_interval.end_pos,
                },
                "heading_tree": block.heading_tree,
            }
            for block in residual_info.resblocks
            if (
                block.char_interval is not None
                and block.char_interval.start_pos is not None
                and block.char_interval.end_pos is not None
            )
        ],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

  @staticmethod
  def get_resblocks_from_json(
      original_doc: Path | str,
      extraction_doc: Path | str,
      json_save_path: Path | str | None = None,
      ignore_code_fence: bool = False,
  ) -> ResidualInfo:
    """Builds cleaned residual blocks from an extraction-result JSON.

    Args:
      original_doc: Path to the original Markdown document.
      extraction_doc: Path to the extraction-result JSON file.
      json_save_path: Optional output path for serialized residual blocks.
      ignore_code_fence: Whether fenced code blocks should be excluded from
        residual blocks.

    Returns:
      A residual info object containing cleaned residual blocks. Before
      residual spans are computed, extraction intervals, TOC intervals, and
      heading intervals are treated as covered. Code-fence intervals are also
      treated as covered when requested.
    """

    original_path = Path(original_doc)
    extraction_path = Path(extraction_doc)

    original_text = original_path.read_text(encoding="utf-8")
    extraction_data = json.loads(extraction_path.read_text(encoding="utf-8"))

    covered_intervals = ResidualInfo._collect_char_intervals(extraction_data)
    covered_intervals.extend(ResidualInfo._collect_toc_intervals(original_text))
    covered_intervals.extend(
        ResidualInfo._collect_heading_intervals(original_text)
    )
    if ignore_code_fence:
      covered_intervals.extend(
          ResidualInfo._collect_code_fence_intervals(original_text)
      )
    merged_intervals = ResidualInfo._merge_intervals(
        covered_intervals, len(original_text)
    )
    residual_intervals = ResidualInfo._get_residual_intervals(
        merged_intervals, len(original_text)
    )
    residual_blocks = ResidualInfo._build_residual_blocks(
        residual_intervals, original_text
    )
    residual_blocks = ResidualInfo._normalize_blocks(residual_blocks)

    residual_info = ResidualInfo(
        original_doc_ref=original_doc,
        extraction_doc_ref=extraction_doc,
        resblocks=residual_blocks,
    )

    if json_save_path is not None:
      ResidualInfo._dump_residual_json(residual_info, Path(json_save_path))

    return residual_info

  @staticmethod
  def get_resblocks_from_json_with_ignore_class(
      original_doc: Path | str,
      extraction_doc: Path | str,
      ignore_class: list[str],
      json_save_path: Path | str | None = None,
      ignore_code_fence: bool = False,
  ) -> ResidualInfo:
    """Builds residual blocks while ignoring selected extraction classes."""

    original_path = Path(original_doc)
    extraction_path = Path(extraction_doc)

    original_text = original_path.read_text(encoding="utf-8")
    extraction_data = json.loads(extraction_path.read_text(encoding="utf-8"))

    covered_intervals = (
        ResidualInfo._collect_char_intervals_with_ignore_class(
            extraction_data, ignore_class
        )
    )
    covered_intervals.extend(ResidualInfo._collect_toc_intervals(original_text))
    covered_intervals.extend(
        ResidualInfo._collect_heading_intervals(original_text)
    )
    if ignore_code_fence:
      covered_intervals.extend(
          ResidualInfo._collect_code_fence_intervals(original_text)
      )
    merged_intervals = ResidualInfo._merge_intervals(
        covered_intervals, len(original_text)
    )
    residual_intervals = ResidualInfo._get_residual_intervals(
        merged_intervals, len(original_text)
    )
    residual_blocks = ResidualInfo._build_residual_blocks(
        residual_intervals, original_text
    )
    residual_blocks = ResidualInfo._normalize_blocks(residual_blocks)

    residual_info = ResidualInfo(
        original_doc_ref=original_doc,
        extraction_doc_ref=extraction_doc,
        resblocks=residual_blocks,
    )

    if json_save_path is not None:
      ResidualInfo._dump_residual_json(residual_info, Path(json_save_path))

    return residual_info


if __name__ == "__main__":
  """Demo: build residual blocks and save them to `blocks.json`."""

  original_doc = r".\docs\dev\KEP\19-Graduate-CronJob-to-Stable\README.md"
  extraction_doc = (
      r".\result\KEP_prompt_v2\19-Graduate-CronJob-to-Stable\pred_"
      r"19-Graduate-CronJob-to-Stable_dschat-chunk1000-structured-"
      r"all_heading.json"
  )
  json_save_path = r".\residual_info_agents\data\blocks_ignore_testcase.json"

  resinfo = ResidualInfo.get_resblocks_from_json(
      original_doc=original_doc,
      extraction_doc=extraction_doc,
      ignore_code_fence=True,
  )
  ResidualInfo.get_resblocks_from_json_with_ignore_class(
      original_doc=resinfo.original_doc_ref,
      extraction_doc=resinfo.extraction_doc_ref,
      ignore_class=["test_case"],
      json_save_path=json_save_path,
      ignore_code_fence=True,
  )
  print(f"Saved {len(resinfo.resblocks)} residual blocks to {json_save_path}")
