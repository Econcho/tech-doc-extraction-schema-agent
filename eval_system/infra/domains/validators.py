"""KEP-specific validation helpers."""

from __future__ import annotations

from .defaults import CLASS_ATTRIBUTE_SCHEMA
from ..core.models import EvalDocument


class KepGoldValidator:
  """Runs lightweight domain-specific gold validation."""

  def validate(self, docs: list[EvalDocument]) -> list[str]:
    """Validate KEP gold docs against the class-level schema."""
    errors: list[str] = []
    for doc in docs:
      if not doc.extractions:
        errors.append(f"KEP gold document has no extractions: {doc.doc_id}")
      for extraction in doc.extractions:
        class_schema = CLASS_ATTRIBUTE_SCHEMA.get(extraction.extraction_class)
        if class_schema is None:
          continue
        required_keys = set(class_schema["required"])
        optional_keys = set(class_schema["optional"])
        allowed_keys = required_keys | optional_keys
        attribute_keys = set(extraction.attributes)
        missing_keys = required_keys - attribute_keys
        illegal_keys = attribute_keys - allowed_keys
        if missing_keys:
          errors.append(
              f"{doc.doc_id}: {extraction.extraction_class} missing required attributes {sorted(missing_keys)}"
          )
        if illegal_keys:
          errors.append(
              f"{doc.doc_id}: {extraction.extraction_class} has illegal attributes {sorted(illegal_keys)}"
          )
    return errors
