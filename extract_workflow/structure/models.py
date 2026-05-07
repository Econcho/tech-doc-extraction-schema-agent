"""Core models for structure-aware chunking."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal
from typing import Mapping

from langextract.core import data
from langextract.core import tokenizer as tokenizer_lib

BlockKind = Literal[
    "heading",
    "paragraph",
    "bullet_item",
    "numbered_item",
    "checklist_item",
    "code_fence",
    "table",
    "blockquote",
]

ContainerKind = Literal[
    "list",
    "prose",
    "qa",
    "subtree",
    "isolated",
]


@dataclass(slots=True)
class StructuredBlock:
  """A structure-aware span over a source document."""

  block_id: str
  token_interval: tokenizer_lib.TokenInterval
  kind: BlockKind
  heading_level: int | None
  heading_path_block_ids: tuple[str, ...]
  parent_block_id: str | None = None
  list_level: int = 0
  indent: int = 0
  metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StructuredDocument:
  """A structured view over a source document."""

  source_document: data.Document
  blocks: tuple[StructuredBlock, ...]
  block_index: Mapping[str, int]
  heading_children: Mapping[str, tuple[str, ...]]


@dataclass(slots=True)
class Container:
  """The smallest unit used for chunk assembly."""

  container_id: str
  kind: ContainerKind
  block_ids: tuple[str, ...]
  token_interval: tokenizer_lib.TokenInterval
  context_block_ids: tuple[str, ...] = ()
  metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContextRef:
  """A lightweight reference to contextual blocks."""

  ref_type: Literal["heading_path", "subtree_anchor"]
  block_ids: tuple[str, ...]
  context_text: str | None = None
