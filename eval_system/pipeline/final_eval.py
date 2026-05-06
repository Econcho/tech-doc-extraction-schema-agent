"""Top-level final evaluation pipeline."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..infra.services import (
    ConfigInfraService,
    DatasetInfraService,
    DomainInfraService,
    GateInfraService,
    MetricInfraService,
    PredictionInfraService,
    ReportInfraService,
    ValidationInfraService,
)


class FinalEvaluationPipeline:
  """Orchestrates one complete final evaluation run."""

  def __init__(self) -> None:
    """Initialize the infrastructure services used by the pipeline."""
    self.configs = ConfigInfraService()
    self.datasets = DatasetInfraService()
    self.domains = DomainInfraService()
    self.validation = ValidationInfraService()
    self.predictions = PredictionInfraService()
    self.metrics = MetricInfraService()
    self.reports = ReportInfraService()
    self.gates = GateInfraService()

  def run(self, config_path: str | Path) -> dict[str, Any]:
    """Run one complete evaluation pipeline from a config file."""
    config = self.configs.load(config_path)
    plugin = self.domains.load_plugin(config["domain_plugin"])
    matching_metric_names, diagnostic_metric_names = self.domains.partition_metric_names(
        plugin,
        config["metrics"],
    )
    context = plugin.build_context(config.get("thresholds", {}))
    self.validation.raise_if_errors(
        self.validation.validate_config(config, config["report"]["output_dir"])
    )

    gold_docs, dataset_info = self.datasets.load_dataset(config["dataset"])
    pred_docs = self.predictions.load_predictions(config, dataset_info, gold_docs)
    self.validation.raise_if_errors(
        self.validation.validate_prediction(
            pred_docs,
            known_doc_ids=set(gold_docs.keys()),
            allowed_classes=set(plugin.get_allowed_classes()),
            allowed_attribute_keys=set(plugin.get_allowed_attribute_keys()),
            class_attribute_schema=plugin.get_class_attribute_schema(),
        )
    )
    registry = self.domains.build_metric_registry(plugin)
    summary = self.metrics.evaluate_documents(
        gold_docs=gold_docs,
        pred_docs=pred_docs,
        plugin=plugin,
        context=context,
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
        dataset_info=dataset_info,
        run_info={
            "prediction_path": config["prediction"]["path"],
            "adapter": config["prediction"]["adapter"],
            "matcher": config["matcher"]["type"],
            "metrics": config["metrics"],
            "matching_metrics": matching_metric_names,
            "diagnostic_metrics": diagnostic_metric_names,
            "thresholds": context.thresholds,
            "tokenizer_name": context.tokenizer_name,
        },
        registry=registry,
    )
    gate_result = self.gates.decide(summary, config.get("gate"))
    report_output_dir = self.reports.write(
        config["report"]["output_dir"],
        summary,
        {
            **config,
            "gate_result": asdict(gate_result),
        },
        config["report"].get("formats", ["json", "markdown"]),
    )
    serialized = self._serialize_summary(summary)
    serialized["gate_result"] = asdict(gate_result)
    serialized["report_output_dir"] = str(report_output_dir)
    return serialized

  def _serialize_summary(self, summary: Any) -> dict[str, Any]:
    """Convert one evaluation summary dataclass into a plain dictionary."""
    return {
        "dataset_info": summary.dataset_info,
        "run_info": summary.run_info,
        "micro_results": {
            name: result.__dict__ for name, result in summary.micro_results.items()
        },
        "macro_doc_results": {
            name: result.__dict__ for name, result in summary.macro_doc_results.items()
        },
        "macro_class_results": {
            metric_name: {
                extraction_class: result.__dict__
                for extraction_class, result in class_results.items()
            }
            for metric_name, class_results in summary.macro_class_results.items()
        },
        "per_doc_results": {
            doc_id: {metric_name: result.__dict__ for metric_name, result in results.items()}
            for doc_id, results in summary.per_doc_results.items()
        },
        "diagnostic_results": {
            name: result.__dict__ for name, result in summary.diagnostic_results.items()
        },
        "per_doc_diagnostic_results": {
            doc_id: {metric_name: result.__dict__ for metric_name, result in results.items()}
            for doc_id, results in summary.per_doc_diagnostic_results.items()
        },
        "error_buckets": summary.error_buckets,
        "error_samples": [entry.__dict__ for entry in summary.error_samples],
    }
