"""Top-level single-file evaluation pipeline."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..infra.services import (
    ConsoleRenderService,
    DatasetInfraService,
    DomainInfraService,
    GateInfraService,
    MetricInfraService,
    PredictionInfraService,
    ValidationInfraService,
)


class SingleFileEvaluationPipeline:
  """Runs the convenience single-file evaluation workflow."""

  def __init__(self) -> None:
    """Initialize the infrastructure services used by the pipeline."""
    self.datasets = DatasetInfraService()
    self.domains = DomainInfraService()
    self.validation = ValidationInfraService()
    self.predictions = PredictionInfraService()
    self.metrics = MetricInfraService()
    self.console = ConsoleRenderService()
    self.gates = GateInfraService()

  def run(
      self,
      gold_path: str | Path,
      pred_path: str | Path,
      *,
      save_result: bool = False,
      save_path: str | Path | None = None,
  ) -> dict[str, Any]:
    """Evaluate one gold file and one prediction file."""
    plugin = self.domains.load_plugin("kep_v1")
    selected_metrics = self.domains.get_supported_metric_names(plugin)
    matching_metric_names, diagnostic_metric_names = self.domains.partition_metric_names(
        plugin,
        selected_metrics,
    )
    context = plugin.build_context({})
    gold_doc = self.datasets.load_single_gold(
        gold_path=gold_path,
        pred_path=pred_path,
        domain="kep",
    )
    pred_doc = self.predictions.load_single_prediction(
        pred_path=pred_path,
        doc_id=gold_doc.doc_id,
        domain="kep",
    )
    self.validation.raise_if_errors(
        self.validation.validate_prediction(
            [pred_doc],
            known_doc_ids={gold_doc.doc_id},
            allowed_classes=set(plugin.get_allowed_classes()),
            allowed_attribute_keys=set(plugin.get_allowed_attribute_keys()),
            class_attribute_schema=plugin.get_class_attribute_schema(),
        )
    )
    registry = self.domains.build_metric_registry(plugin)
    summary = self.metrics.evaluate_documents(
        gold_docs={gold_doc.doc_id: gold_doc},
        pred_docs=[pred_doc],
        plugin=plugin,
        context=context,
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
        dataset_info={
            "dataset_name": "single_file_eval",
            "version": "ad_hoc",
            "domain": "kep",
            "schema_version": "kep_schema_v1",
            "label_policy_version": "eval_policy_v1",
            "split": "single",
            "doc_count": 1,
        },
        run_info={
            "gold_path": str(gold_path),
            "prediction_path": str(pred_path),
            "adapter": "langextract",
            "matcher": "max_weight_bipartite",
            "metrics": selected_metrics,
            "matching_metrics": matching_metric_names,
            "diagnostic_metrics": diagnostic_metric_names,
            "thresholds": context.thresholds,
            "tokenizer_name": context.tokenizer_name,
        },
        registry=registry,
    )
    gate_result = self.gates.decide(summary)
    serialized = self._serialize_summary(summary)
    serialized["gate_result"] = asdict(gate_result)
    console_output = self.console.build_single_file_result(
        serialized["micro_results"],
        serialized["diagnostic_results"],
    )
    print(console_output)
    if save_result:
      output_path = self._resolve_output_path(pred_path, save_path)
      output_path.parent.mkdir(parents=True, exist_ok=True)
      output_path.write_text(console_output, encoding="utf-8")
    return serialized

  def _resolve_output_path(
      self,
      pred_path: str | Path,
      save_path: str | Path | None,
  ) -> Path:
    """Resolve the output path used by the single-file convenience pipeline."""
    if save_path is not None:
      return Path(save_path)
    pred_file = Path(pred_path)
    return pred_file.with_name(f"{pred_file.stem}_eval.txt")

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
