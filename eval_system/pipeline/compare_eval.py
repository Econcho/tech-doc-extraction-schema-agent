"""Top-level compare/regression evaluation pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..infra.services import (
    ConfigInfraService,
    DatasetInfraService,
    DomainInfraService,
    MetricInfraService,
    PredictionInfraService,
    ReportInfraService,
    ValidationInfraService,
)


class CompareEvaluationPipeline:
  """Orchestrates baseline-vs-candidate comparison evaluation."""

  def __init__(self) -> None:
    """Initialize the infrastructure services used by the compare pipeline."""
    self.configs = ConfigInfraService()
    self.datasets = DatasetInfraService()
    self.domains = DomainInfraService()
    self.validation = ValidationInfraService()
    self.predictions = PredictionInfraService()
    self.metrics = MetricInfraService()
    self.reports = ReportInfraService()

  def run(self, config_path: str | Path) -> dict[str, Any]:
    """Run one baseline-vs-candidate comparison from a config file."""
    config = self.configs.load(config_path)
    plugin = self.domains.load_plugin(config["domain_plugin"])
    matching_metric_names, diagnostic_metric_names = self.domains.partition_metric_names(
        plugin,
        config["metrics"],
    )
    context = plugin.build_context(config.get("thresholds", {}))
    self.validation.raise_if_errors(
        self.validation.validate_compare_config(config, config["report"]["output_dir"])
    )

    gold_docs, dataset_info = self.datasets.load_dataset(config["dataset"])
    registry = self.domains.build_metric_registry(plugin)

    baseline_summary = self._run_variant(
        variant_name="baseline",
        prediction_config=config["baseline"],
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
        gold_docs=gold_docs,
        dataset_info=dataset_info,
        plugin=plugin,
        context=context,
        registry=registry,
    )
    candidate_summary = self._run_variant(
        variant_name="candidate",
        prediction_config=config["candidate"],
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
        gold_docs=gold_docs,
        dataset_info=dataset_info,
        plugin=plugin,
        context=context,
        registry=registry,
    )

    comparison = self._build_comparison_payload(
        dataset_info=dataset_info,
        config=config,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
    )
    report_output_dir = self.reports.write_comparison(
        config["report"]["output_dir"],
        comparison,
        config,
        config["report"].get("formats", ["json", "markdown"]),
    )
    comparison["report_output_dir"] = str(report_output_dir)
    return comparison

  def _run_variant(
      self,
      *,
      variant_name: str,
      prediction_config: dict[str, Any],
      matching_metric_names: list[str],
      diagnostic_metric_names: list[str],
      gold_docs: dict[str, Any],
      dataset_info: dict[str, Any],
      plugin: Any,
      context: Any,
      registry: Any,
  ) -> dict[str, Any]:
    """Run one side of the comparison and serialize its summary."""
    run_config = {
        "prediction": prediction_config,
    }
    pred_docs = self.predictions.load_predictions(run_config, dataset_info, gold_docs)
    self.validation.raise_if_errors(
        self.validation.validate_prediction(
            pred_docs,
            known_doc_ids=set(gold_docs.keys()),
            allowed_classes=set(plugin.get_allowed_classes()),
            allowed_attribute_keys=set(plugin.get_allowed_attribute_keys()),
            class_attribute_schema=plugin.get_class_attribute_schema(),
        )
    )
    summary = self.metrics.evaluate_documents(
        gold_docs=gold_docs,
        pred_docs=pred_docs,
        plugin=plugin,
        context=context,
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
        dataset_info=dataset_info,
        run_info={
            "variant": variant_name,
            "prediction_path": prediction_config["path"],
            "adapter": prediction_config["adapter"],
            "matching_metrics": matching_metric_names,
            "diagnostic_metrics": diagnostic_metric_names,
            "thresholds": context.thresholds,
            "tokenizer_name": context.tokenizer_name,
        },
        registry=registry,
    )
    return self._serialize_summary(summary)

  def _build_comparison_payload(
      self,
      *,
      dataset_info: dict[str, Any],
      config: dict[str, Any],
      baseline_summary: dict[str, Any],
      candidate_summary: dict[str, Any],
      matching_metric_names: list[str],
      diagnostic_metric_names: list[str],
  ) -> dict[str, Any]:
    """Build the final comparison payload."""
    delta_summary = {
        "micro_results": self._build_matching_delta_map(
            baseline_summary["micro_results"],
            candidate_summary["micro_results"],
            matching_metric_names,
        ),
        "macro_doc_results": self._build_matching_delta_map(
            baseline_summary["macro_doc_results"],
            candidate_summary["macro_doc_results"],
            matching_metric_names,
        ),
        "macro_class_results": self._build_macro_class_delta_map(
            baseline_summary["macro_class_results"],
            candidate_summary["macro_class_results"],
            matching_metric_names,
        ),
        "diagnostic_results": self._build_diagnostic_delta_map(
            baseline_summary["diagnostic_results"],
            candidate_summary["diagnostic_results"],
            diagnostic_metric_names,
        ),
        "error_buckets": self._build_error_bucket_delta_map(
            baseline_summary["error_buckets"],
            candidate_summary["error_buckets"],
        ),
    }
    per_doc_comparison = self._build_per_doc_comparison(
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        matching_metric_names=matching_metric_names,
        diagnostic_metric_names=diagnostic_metric_names,
    )
    regression_summary = self._build_regression_summary(delta_summary)
    return {
        "dataset_info": dataset_info,
        "compare_info": {
            "baseline_prediction_path": config["baseline"]["path"],
            "candidate_prediction_path": config["candidate"]["path"],
            "baseline_filename_template": config["baseline"].get("filename_template"),
            "candidate_filename_template": config["candidate"].get("filename_template"),
            "metrics": config["metrics"],
            "matching_metrics": matching_metric_names,
            "diagnostic_metrics": diagnostic_metric_names,
            "thresholds": config.get("thresholds", {}),
        },
        "baseline_summary": baseline_summary,
        "candidate_summary": candidate_summary,
        "delta_summary": delta_summary,
        "per_doc_comparison": per_doc_comparison,
        "regression_summary": regression_summary,
    }

  def _build_matching_delta_map(
      self,
      baseline_metrics: dict[str, Any],
      candidate_metrics: dict[str, Any],
      metric_names: list[str],
  ) -> dict[str, dict[str, float]]:
    """Build delta payloads for matching metrics."""
    return {
        metric_name: {
            "baseline_precision": baseline_metrics[metric_name]["precision"],
            "candidate_precision": candidate_metrics[metric_name]["precision"],
            "precision_delta": candidate_metrics[metric_name]["precision"] - baseline_metrics[metric_name]["precision"],
            "baseline_recall": baseline_metrics[metric_name]["recall"],
            "candidate_recall": candidate_metrics[metric_name]["recall"],
            "recall_delta": candidate_metrics[metric_name]["recall"] - baseline_metrics[metric_name]["recall"],
            "baseline_f1": baseline_metrics[metric_name]["f1"],
            "candidate_f1": candidate_metrics[metric_name]["f1"],
            "f1_delta": candidate_metrics[metric_name]["f1"] - baseline_metrics[metric_name]["f1"],
        }
        for metric_name in metric_names
    }

  def _build_macro_class_delta_map(
      self,
      baseline_metrics: dict[str, Any],
      candidate_metrics: dict[str, Any],
      metric_names: list[str],
  ) -> dict[str, dict[str, dict[str, float]]]:
    """Build delta payloads for class-level macro metrics."""
    payload: dict[str, dict[str, dict[str, float]]] = {}
    for metric_name in metric_names:
      baseline_class_results = baseline_metrics.get(metric_name, {})
      candidate_class_results = candidate_metrics.get(metric_name, {})
      class_names = sorted(set(baseline_class_results.keys()) | set(candidate_class_results.keys()))
      payload[metric_name] = {}
      for class_name in class_names:
        baseline_result = baseline_class_results.get(
            class_name,
            {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        )
        candidate_result = candidate_class_results.get(
            class_name,
            {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        )
        payload[metric_name][class_name] = {
            "baseline_precision": baseline_result["precision"],
            "candidate_precision": candidate_result["precision"],
            "precision_delta": candidate_result["precision"] - baseline_result["precision"],
            "baseline_recall": baseline_result["recall"],
            "candidate_recall": candidate_result["recall"],
            "recall_delta": candidate_result["recall"] - baseline_result["recall"],
            "baseline_f1": baseline_result["f1"],
            "candidate_f1": candidate_result["f1"],
            "f1_delta": candidate_result["f1"] - baseline_result["f1"],
        }
    return payload

  def _build_diagnostic_delta_map(
      self,
      baseline_metrics: dict[str, Any],
      candidate_metrics: dict[str, Any],
      metric_names: list[str],
  ) -> dict[str, dict[str, float]]:
    """Build delta payloads for diagnostic metrics."""
    return {
        metric_name: {
            "baseline_value": baseline_metrics[metric_name]["value"],
            "candidate_value": candidate_metrics[metric_name]["value"],
            "value_delta": candidate_metrics[metric_name]["value"] - baseline_metrics[metric_name]["value"],
        }
        for metric_name in metric_names
    }

  def _build_error_bucket_delta_map(
      self,
      baseline_buckets: dict[str, int],
      candidate_buckets: dict[str, int],
  ) -> dict[str, dict[str, int]]:
    """Build delta payloads for error buckets."""
    bucket_names = sorted(set(baseline_buckets.keys()) | set(candidate_buckets.keys()))
    return {
        bucket_name: {
            "baseline_count": baseline_buckets.get(bucket_name, 0),
            "candidate_count": candidate_buckets.get(bucket_name, 0),
            "count_delta": candidate_buckets.get(bucket_name, 0) - baseline_buckets.get(bucket_name, 0),
        }
        for bucket_name in bucket_names
    }

  def _build_per_doc_comparison(
      self,
      *,
      baseline_summary: dict[str, Any],
      candidate_summary: dict[str, Any],
      matching_metric_names: list[str],
      diagnostic_metric_names: list[str],
  ) -> dict[str, Any]:
    """Build the per-document comparison payload."""
    doc_ids = sorted(
        set(baseline_summary["per_doc_results"].keys())
        | set(candidate_summary["per_doc_results"].keys())
    )
    payload: dict[str, Any] = {}
    for doc_id in doc_ids:
      baseline_doc_metrics = baseline_summary["per_doc_results"].get(doc_id, {})
      candidate_doc_metrics = candidate_summary["per_doc_results"].get(doc_id, {})
      baseline_doc_diagnostics = baseline_summary["per_doc_diagnostic_results"].get(doc_id, {})
      candidate_doc_diagnostics = candidate_summary["per_doc_diagnostic_results"].get(doc_id, {})
      payload[doc_id] = {
          "matching_metrics": {
              metric_name: {
                  "baseline": baseline_doc_metrics[metric_name],
                  "candidate": candidate_doc_metrics[metric_name],
                  "delta": {
                      "precision_delta": candidate_doc_metrics[metric_name]["precision"] - baseline_doc_metrics[metric_name]["precision"],
                      "recall_delta": candidate_doc_metrics[metric_name]["recall"] - baseline_doc_metrics[metric_name]["recall"],
                      "f1_delta": candidate_doc_metrics[metric_name]["f1"] - baseline_doc_metrics[metric_name]["f1"],
                  },
              }
              for metric_name in matching_metric_names
          },
          "diagnostic_metrics": {
              metric_name: {
                  "baseline_value": baseline_doc_diagnostics[metric_name]["value"],
                  "candidate_value": candidate_doc_diagnostics[metric_name]["value"],
                  "value_delta": candidate_doc_diagnostics[metric_name]["value"] - baseline_doc_diagnostics[metric_name]["value"],
              }
              for metric_name in diagnostic_metric_names
          },
      }
    return payload

  def _build_regression_summary(self, delta_summary: dict[str, Any]) -> dict[str, Any]:
    """Build the overall regression summary."""
    all_metric_deltas: dict[str, float] = {
        metric_name: metric_payload["f1_delta"]
        for metric_name, metric_payload in delta_summary["micro_results"].items()
    }
    for metric_name, metric_payload in delta_summary["diagnostic_results"].items():
      direction = -metric_payload["value_delta"] if metric_name == "structure_anomaly_rate" else metric_payload["value_delta"]
      all_metric_deltas[metric_name] = direction

    improved = sum(1 for value in all_metric_deltas.values() if value > 0)
    degraded = sum(1 for value in all_metric_deltas.values() if value < 0)
    unchanged = sum(1 for value in all_metric_deltas.values() if value == 0)

    structured_relaxed_delta = delta_summary["micro_results"]["structured_relaxed"]["f1_delta"]
    structured_strict_delta = delta_summary["micro_results"]["structured_strict"]["f1_delta"]
    anomaly_delta = delta_summary["diagnostic_results"].get("structure_anomaly_rate", {}).get("value_delta", 0.0)

    if structured_relaxed_delta > 0 and structured_strict_delta >= 0 and anomaly_delta <= 0:
      overall_assessment = "candidate 相比 baseline 呈现明确提升"
    elif structured_relaxed_delta < 0 or structured_strict_delta < 0:
      overall_assessment = "candidate 相比 baseline 存在回归风险"
    else:
      overall_assessment = "candidate 相比 baseline 变化有限"

    if structured_relaxed_delta > 0:
      core_metric_assessment = "核心结构化指标提升"
    elif structured_relaxed_delta < 0:
      core_metric_assessment = "核心结构化指标退化"
    else:
      core_metric_assessment = "核心结构化指标持平"

    return {
        "overall_assessment": overall_assessment,
        "core_metric_assessment": core_metric_assessment,
        "improved_metric_count": improved,
        "degraded_metric_count": degraded,
        "unchanged_metric_count": unchanged,
    }

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
