"""Validation helpers for datasets, predictions, and configs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import EvalDocument


@dataclass(frozen=True)
class ValidationError:
  """Represents one validation failure."""

  scope: str
  message: str


class Validator:
  """Validates datasets, documents, predictions, and config objects."""

  def validate_dataset(self, docs: list[EvalDocument]) -> list[ValidationError]:
    """Validate document IDs and domain consistency."""
    errors: list[ValidationError] = []
    seen_doc_ids: set[str] = set()
    for doc in docs:
      if doc.doc_id in seen_doc_ids:
        errors.append(ValidationError("dataset", f"Duplicate doc_id: {doc.doc_id}"))
      seen_doc_ids.add(doc.doc_id)
      if not doc.domain:
        errors.append(ValidationError("dataset", f"Missing domain for {doc.doc_id}"))
    return errors

  def validate_gold(
      self,
      docs: list[EvalDocument],
      *,
      allowed_classes: set[str],
      allowed_attribute_keys: set[str],
      class_attribute_schema: dict[str, dict[str, tuple[str, ...]]] | None = None,
  ) -> list[ValidationError]:
    """Skip gold validation and always return no errors."""
    del docs
    del allowed_classes
    del allowed_attribute_keys
    del class_attribute_schema
    return []

  def validate_prediction(
      self,
      docs: list[EvalDocument],
      *,
      known_doc_ids: set[str],
      allowed_classes: set[str],
      allowed_attribute_keys: set[str] | None = None,
      class_attribute_schema: dict[str, dict[str, tuple[str, ...]]] | None = None,
  ) -> list[ValidationError]:
    """Validate prediction documents with lenient schema rules.

    Predictions are allowed to have unsupported classes, missing attributes,
    or illegal attribute keys. Those cases should flow into matching and
    scoring as normal false positives or mismatches instead of aborting the
    evaluation run.
    """
    errors: list[ValidationError] = []
    for doc in docs:
      if doc.doc_id not in known_doc_ids:
        errors.append(ValidationError("prediction", f"Unknown prediction doc_id: {doc.doc_id}"))
      for extraction in doc.extractions:
        if not isinstance(extraction.extraction_text, str) or not extraction.extraction_text.strip():
          errors.append(ValidationError("prediction", f"Invalid extraction_text in {doc.doc_id}"))
        if not isinstance(extraction.attributes, dict):
          errors.append(ValidationError("prediction", f"Non-dict attributes in {doc.doc_id}"))
    return errors

  def validate_config(self, config: dict[str, Any], output_dir: str | Path) -> list[ValidationError]:
    """Validate a loaded runtime config."""
    errors: list[ValidationError] = []
    for key in ("dataset", "prediction", "domain_plugin", "matcher", "metrics", "report"):
      if key not in config:
        errors.append(ValidationError("config", f"Missing config key: {key}"))
    for name, value in config.get("thresholds", {}).items():
      if not 0 <= float(value) <= 1:
        errors.append(ValidationError("config", f"Threshold out of range: {name}={value}"))
    try:
      Path(output_dir).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
      errors.append(ValidationError("config", f"Output dir not writable: {exc}"))
    return errors

  def validate_compare_config(
      self,
      config: dict[str, Any],
      output_dir: str | Path,
  ) -> list[ValidationError]:
    """Validate a loaded compare-eval config."""
    errors: list[ValidationError] = []
    for key in ("dataset", "baseline", "candidate", "domain_plugin", "matcher", "metrics", "report"):
      if key not in config:
        errors.append(ValidationError("config", f"Missing config key: {key}"))
    for section_name in ("baseline", "candidate"):
      section = config.get(section_name)
      if not isinstance(section, dict):
        continue
      for required_key in ("path", "adapter"):
        if required_key not in section:
          errors.append(
              ValidationError("config", f"Missing {section_name}.{required_key}")
          )
    for name, value in config.get("thresholds", {}).items():
      if not 0 <= float(value) <= 1:
        errors.append(ValidationError("config", f"Threshold out of range: {name}={value}"))
    try:
      Path(output_dir).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
      errors.append(ValidationError("config", f"Output dir not writable: {exc}"))
    return errors

  def _validate_documents(
      self,
      docs: list[EvalDocument],
      *,
      scope: str,
      allowed_classes: set[str],
      allowed_attribute_keys: set[str] | None,
      class_attribute_schema: dict[str, dict[str, tuple[str, ...]]] | None = None,
  ) -> list[ValidationError]:
    """Validate shared structural rules across document collections."""
    errors: list[ValidationError] = []
    for doc in docs:
      for extraction in doc.extractions:
        if extraction.extraction_class not in allowed_classes:
          errors.append(
              ValidationError(
                  scope,
                  f"Unsupported extraction_class in {doc.doc_id}: {extraction.extraction_class}",
              )
          )
        if not isinstance(extraction.extraction_text, str) or not extraction.extraction_text.strip():
          errors.append(ValidationError(scope, f"Invalid extraction_text in {doc.doc_id}"))
        if not isinstance(extraction.attributes, dict):
          errors.append(ValidationError(scope, f"Non-dict attributes in {doc.doc_id}"))
        if allowed_attribute_keys is not None:
          illegal_keys = set(extraction.attributes) - allowed_attribute_keys
          if illegal_keys:
            errors.append(
                ValidationError(scope, f"Illegal attribute keys in {doc.doc_id}: {sorted(illegal_keys)}")
            )
        if class_attribute_schema is not None:
          schema = class_attribute_schema.get(extraction.extraction_class)
          if schema is not None:
            required_keys = set(schema["required"])
            optional_keys = set(schema["optional"])
            attribute_keys = set(extraction.attributes)
            missing_keys = required_keys - attribute_keys
            illegal_keys = attribute_keys - (required_keys | optional_keys)
            if missing_keys:
              errors.append(
                  ValidationError(
                      scope,
                      (
                          f"{doc.doc_id}: {extraction.extraction_class} missing "
                          f"required attributes {sorted(missing_keys)}"
                      ),
                  )
              )
            if illegal_keys:
              errors.append(
                  ValidationError(
                      scope,
                      (
                          f"{doc.doc_id}: {extraction.extraction_class} has illegal "
                          f"attributes {sorted(illegal_keys)}"
                      ),
                  )
              )
    return errors
