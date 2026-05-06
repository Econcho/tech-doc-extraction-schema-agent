"""Top-level validation pipeline."""

from __future__ import annotations

from pathlib import Path

from ..infra.services import (
    ConfigInfraService,
    DatasetInfraService,
    DomainInfraService,
    PredictionInfraService,
    ValidationInfraService,
)


class ValidationPipeline:
  """Provides validation-only orchestration flows."""

  def __init__(self) -> None:
    """Initialize the infrastructure services used by the pipeline."""
    self.configs = ConfigInfraService()
    self.datasets = DatasetInfraService()
    self.domains = DomainInfraService()
    self.predictions = PredictionInfraService()
    self.validation = ValidationInfraService()

  def validate_dataset(self, config_path: str | Path) -> list[dict[str, str]]:
    """Validate only the loaded gold dataset."""
    config = self.configs.load(config_path)
    gold_docs, _ = self.datasets.load_dataset(config["dataset"])
    errors = self.validation.validate_dataset(list(gold_docs.values()))
    return [error.__dict__ for error in errors]

  def validate_prediction(self, config_path: str | Path) -> list[dict[str, str]]:
    """Validate only the loaded prediction data."""
    config = self.configs.load(config_path)
    plugin = self.domains.load_plugin(config["domain_plugin"])
    gold_docs, dataset_info = self.datasets.load_dataset(config["dataset"])
    pred_docs = self.predictions.load_predictions(config, dataset_info, gold_docs)
    errors = self.validation.validate_prediction(
        pred_docs,
        known_doc_ids=set(gold_docs.keys()),
        allowed_classes=set(plugin.get_allowed_classes()),
        allowed_attribute_keys=set(plugin.get_allowed_attribute_keys()),
        class_attribute_schema=plugin.get_class_attribute_schema(),
    )
    return [error.__dict__ for error in errors]
