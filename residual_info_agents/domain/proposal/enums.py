from __future__ import annotations

import enum


class BucketProposalType(str, enum.Enum):
  NEW_SCHEMA = "new_schema"
  NEW_ATTR = "new_attr"


class BucketStatus(str, enum.Enum):
  INCUBATING = "incubating"
  STABLE = "stable"
  STALE = "stale"
  AMBIGUOUS = "ambiguous"
  SPLIT = "split"
  MERGED = "merged"
  ARCHIVED = "archived"
  REJECTED = "rejected"


class SignalBucketMappingStatus(str, enum.Enum):
  ACTIVE = "active"
  REMOVED = "removed"
  REMAPPED = "remapped"
  MERGED = "merged"
  REJECTED = "rejected"


class ProposalStatus(str, enum.Enum):
  DRAFT = "draft"
  CHECKED = "checked"
  CONFLICT = "conflict"
  ACCEPTED = "accepted"
  REJECTED = "rejected"
  NEEDS_REVISION = "needs_revision"
