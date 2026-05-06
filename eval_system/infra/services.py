"""Infrastructure services built on top of the low-level evaluation modules."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from .adapters.json_adapter import JsonAdapter
from .adapters.langextract_adapter import LangExtractAdapter
from .core.aggregation import Aggregator
from .core.config import ConfigLoader
from .core.error_buckets import ErrorBucketAnalyzer
from .core.matching import MaxWeightBipartiteMatcher
from .core.models import EvalDocument, EvalExtraction, EvaluationSummary
from .core.report import ReportWriter
from .core.validation import ValidationError, Validator
from .datasets.loader import DatasetLoader
from .domains.plugin import KepDomainPlugin
from .metrics.classification import ClassificationMetric
from .metrics.detection import DetectionMetric
from .metrics.grounding_accuracy import GroundingAccuracyMetric
from .metrics.registry import MetricRegistry
from .metrics.structure_anomaly import StructureAnomalyMetric
from .metrics.structured import StructuredMetric
from .models import GateDecision


MATCHING_METRIC_NAMES = (
    "detection_strict",
    "detection_relaxed",
    "class_strict",
    "class_relaxed",
    "structured_strict",
    "structured_relaxed",
)

DIAGNOSTIC_METRIC_NAMES = (
    "structure_anomaly_rate",
    "grounding_match_exact_rate",
    "grounding_match_lesser_rate",
    "grounding_match_fuzzy_rate",
    "grounding_match_none_rate",
)


class DomainInfraService:
  """Resolves domain plugins and metric registries."""

  def load_plugin(self, plugin_name: str) -> KepDomainPlugin:
    """Resolve one supported domain plugin by name."""
    if plugin_name != "kep_v1":
      raise ValueError(f"Unsupported domain plugin: {plugin_name}")
    return KepDomainPlugin()

  def build_metric_registry(self, plugin: KepDomainPlugin) -> MetricRegistry:
    """Build the registry of core matching metrics for one domain plugin."""
    registry = MetricRegistry()
    registry.register(DetectionMetric("detection_strict", relaxed=False, plugin=plugin))
    registry.register(DetectionMetric("detection_relaxed", relaxed=True, plugin=plugin))
    registry.register(ClassificationMetric("class_strict", relaxed=False, plugin=plugin))
    registry.register(ClassificationMetric("class_relaxed", relaxed=True, plugin=plugin))
    registry.register(StructuredMetric("structured_strict", relaxed=False, plugin=plugin))
    registry.register(StructuredMetric("structured_relaxed", relaxed=True, plugin=plugin))
    return registry

  def get_supported_metric_names(self, plugin: KepDomainPlugin) -> list[str]:
    """Return all supported matching and diagnostic metric names."""
    del plugin
    return [*MATCHING_METRIC_NAMES, *DIAGNOSTIC_METRIC_NAMES]

  def partition_metric_names(
      self,
      plugin: KepDomainPlugin,
      metric_names: list[str],
  ) -> tuple[list[str], list[str]]:
    """Split configured metric names into matching and diagnostic groups."""
    supported = set(self.get_supported_metric_names(plugin))
    unknown = [name for name in metric_names if name not in supported]
    if unknown:
      raise ValueError(
          f"Unsupported metrics: {unknown}. Supported metrics: {sorted(supported)}"
      )
    matching = [name for name in metric_names if name in MATCHING_METRIC_NAMES]
    diagnostic = [name for name in metric_names if name in DIAGNOSTIC_METRIC_NAMES]
    return matching, diagnostic


class DatasetInfraService:
  """Loads gold documents from one registry-defined evaluation subset."""

  def __init__(self) -> None:
    """Initialize the underlying dataset loader."""
    self.loader = DatasetLoader()

  def load_dataset(self, dataset_config: dict[str, Any]) -> tuple[dict[str, EvalDocument], dict]:
    """Load a gold dataset from the configured registry file."""
    registry_path = dataset_config.get("registry_path")
    if not registry_path:
      raise ValueError("dataset.registry_path is required. Legacy manifest/split datasets are no longer supported.")
    return self.loader.load_registry(registry_path)

  def load_single_gold(
      self,
      *,
      gold_path: str | Path,
      pred_path: str | Path,
      domain: str,
  ) -> EvalDocument:
    """Load one gold annotation JSON file into the internal document model."""
    gold_file = Path(gold_path)
    payload = json.loads(gold_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
      raise ValueError("Gold annotation file must be a JSON array.")
    doc_id = self._infer_doc_id(gold_file, Path(pred_path))
    return EvalDocument(
        doc_id=doc_id,
        domain=domain,
        split="single",
        extractions=tuple(
            EvalExtraction(
                extraction_class=item["extraction_class"],
                extraction_text=item["extraction_text"],
                attributes=item.get("attributes") or {},
            )
            for item in payload
        ),
    )

  def _infer_doc_id(self, gold_path: Path, pred_path: Path) -> str:
    """Infer one document identifier from a gold file path and prediction path."""
    doc_id = gold_path.stem
    if doc_id.startswith("label"):
      pred_stem = pred_path.stem
      if pred_stem.startswith("pred_"):
        return pred_stem.removeprefix("pred_")
    if doc_id.endswith("_v1"):
      return doc_id[:-3]
    return doc_id


class PredictionInfraService:
  """Loads prediction documents through the configured adapter."""

  def load_predictions(
      self,
      config: dict[str, Any],
      dataset_info: dict[str, Any],
      gold_docs: dict[str, EvalDocument],
  ) -> list[EvalDocument]:
    """Load prediction documents for one evaluation run."""
    prediction_path = Path(config["prediction"]["path"])
    adapter_name = config["prediction"]["adapter"]
    adapter = self._resolve_adapter(adapter_name)
    prediction_config = config["prediction"]

    if not prediction_path.exists():
      raise FileNotFoundError(f"Prediction path not found: {prediction_path}")

    if prediction_path.is_file():
      return adapter.load(
          str(prediction_path),
          doc_id=prediction_config.get("doc_id"),
          domain=dataset_info["domain"],
          split=dataset_info["split"],
      )

    docs: list[EvalDocument] = []
    for doc_id in gold_docs:
      per_doc_path = self._resolve_per_doc_prediction_path(
          prediction_root=prediction_path,
          doc_id=doc_id,
          prediction_config=prediction_config,
      )
      if per_doc_path.exists():
        docs.extend(
            adapter.load(
                str(per_doc_path),
                doc_id=doc_id,
                domain=dataset_info["domain"],
                split=dataset_info["split"],
            )
        )
    if not docs:
      raise FileNotFoundError(
          "No prediction documents were loaded. "
          "Check prediction.path, filename_template, and doc_subdir."
      )
    return docs

  def load_single_prediction(
      self,
      *,
      pred_path: str | Path,
      doc_id: str,
      domain: str,
  ) -> EvalDocument:
    """Load one prediction file into the internal document model."""
    return LangExtractAdapter().load(
        str(pred_path),
        doc_id=doc_id,
        domain=domain,
        split="single",
    )[0]

  def _resolve_adapter(self, adapter_name: str) -> Any:
    """Resolve one prediction adapter implementation."""
    if adapter_name == "langextract":
      return LangExtractAdapter()
    if adapter_name == "json":
      return JsonAdapter()
    raise ValueError(f"Unsupported adapter: {adapter_name}")

  def _resolve_per_doc_prediction_path(
      self,
      *,
      prediction_root: Path,
      doc_id: str,
      prediction_config: dict[str, Any],
  ) -> Path:
    """Resolve one per-document prediction path under directory mode."""
    base_dir = prediction_root / doc_id if prediction_config.get("doc_subdir") else prediction_root
    filename_template = prediction_config.get("filename_template")
    if filename_template:
      return base_dir / filename_template.format(doc_id=doc_id)
    return base_dir / f"{doc_id}.json"


class ValidationInfraService:
  """Encapsulates config, dataset, and prediction validation behavior."""

  def __init__(self) -> None:
    """Initialize the shared validator."""
    self.validator = Validator()

  def validate_config(
      self,
      config: dict[str, Any],
      output_dir: str | Path,
  ) -> list[ValidationError]:
    """Validate one loaded runtime config."""
    return self.validator.validate_config(config, output_dir)

  def validate_compare_config(
      self,
      config: dict[str, Any],
      output_dir: str | Path,
  ) -> list[ValidationError]:
    """Validate one loaded compare-eval config."""
    return self.validator.validate_compare_config(config, output_dir)

  def validate_dataset(self, docs: list[EvalDocument]) -> list[ValidationError]:
    """Validate the loaded gold document collection."""
    return self.validator.validate_dataset(docs)

  def validate_prediction(
      self,
      docs: list[EvalDocument],
      *,
      known_doc_ids: set[str],
      allowed_classes: set[str],
      allowed_attribute_keys: set[str],
      class_attribute_schema: dict[str, dict[str, tuple[str, ...]]],
  ) -> list[ValidationError]:
    """Validate prediction documents against the selected domain plugin."""
    return self.validator.validate_prediction(
        docs,
        known_doc_ids=known_doc_ids,
        allowed_classes=allowed_classes,
        allowed_attribute_keys=allowed_attribute_keys,
        class_attribute_schema=class_attribute_schema,
    )

  def raise_if_errors(self, errors: list[ValidationError]) -> None:
    """Raise one aggregated error when any validation issue is present."""
    if errors:
      raise ValueError([error.message for error in errors])


class MetricInfraService:
  """Runs matching metrics, diagnostics, and aggregation over a document set."""

  def __init__(self) -> None:
    """Initialize reusable matching and aggregation collaborators."""
    self.matcher = MaxWeightBipartiteMatcher()
    self.aggregator = Aggregator()
    self.error_analyzer = ErrorBucketAnalyzer()

  def evaluate_documents(
      self,
      *,
      gold_docs: dict[str, EvalDocument],
      pred_docs: list[EvalDocument],
      plugin: KepDomainPlugin,
      context: Any,
      matching_metric_names: list[str],
      diagnostic_metric_names: list[str],
      dataset_info: dict[str, Any],
      run_info: dict[str, Any],
      registry: MetricRegistry,
  ) -> EvaluationSummary:
    """Run the shared evaluation math on the provided document collection."""
    per_doc_results: dict[str, dict[str, Any]] = defaultdict(dict)
    micro_match_results: dict[str, list[Any]] = defaultdict(list)
    macro_class_match_results: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    anomaly_metric = StructureAnomalyMetric()
    grounding_metric = GroundingAccuracyMetric()
    per_doc_diagnostic_results: dict[str, dict[str, Any]] = defaultdict(dict)
    anomaly_inputs: list[Any] = []
    grounding_inputs: list[dict[str, Any]] = []
    all_error_entries = []

    for pred_doc in pred_docs:
      gold_doc = gold_docs[pred_doc.doc_id]
      if anomaly_metric.name in diagnostic_metric_names:
        anomaly_result = anomaly_metric.score_document(
            pred_doc,
            allowed_classes=set(plugin.get_allowed_classes()),
            class_attribute_schema=plugin.get_class_attribute_schema(),
            attribute_value_schema=plugin.get_attribute_value_schema(),
        )
        per_doc_diagnostic_results[pred_doc.doc_id][anomaly_metric.name] = anomaly_result
        anomaly_inputs.append(anomaly_result)
      if any(name in diagnostic_metric_names for name in grounding_metric.metric_names):
        grounding_results = grounding_metric.score_document(pred_doc)
        for metric_name in diagnostic_metric_names:
          if metric_name in grounding_results:
            per_doc_diagnostic_results[pred_doc.doc_id][metric_name] = grounding_results[metric_name]
        grounding_inputs.append(grounding_results)
      doc_metric_matches = {}
      for metric_name in matching_metric_names:
        metric = registry.get(metric_name)
        pair_rule = metric.build_pair_rule(context)
        match_result = self.matcher.match(
            list(pred_doc.extractions),
            list(gold_doc.extractions),
            pair_rule,
            metric_name=metric_name,
            doc_id=pred_doc.doc_id,
        )
        doc_metric_matches[metric_name] = match_result
        per_doc_results[pred_doc.doc_id][metric_name] = metric.score(match_result)
        micro_match_results[metric_name].append(match_result)

        for extraction_class in plugin.get_allowed_classes():
          class_pred = [
              item for item in pred_doc.extractions if item.extraction_class == extraction_class
          ]
          class_gold = [
              item for item in gold_doc.extractions if item.extraction_class == extraction_class
          ]
          class_match_result = self.matcher.match(
              class_pred,
              class_gold,
              pair_rule,
              metric_name=metric_name,
              doc_id=pred_doc.doc_id,
          )
          macro_class_match_results[metric_name].append(
              (extraction_class, class_match_result)
          )

      if all(
          name in doc_metric_matches
          for name in ("detection_relaxed", "class_relaxed", "structured_relaxed")
      ):
        all_error_entries.extend(
            self.error_analyzer.analyze(
                doc_id=pred_doc.doc_id,
                preds=list(pred_doc.extractions),
                golds=list(gold_doc.extractions),
                detection_relaxed=doc_metric_matches["detection_relaxed"],
                class_relaxed=doc_metric_matches["class_relaxed"],
                structured_relaxed=doc_metric_matches["structured_relaxed"],
            )
        )

    micro_results = {
        metric_name: self.aggregator.aggregate_micro(metric_name, match_results)
        for metric_name, match_results in micro_match_results.items()
    }
    macro_doc_results = {
        metric_name: self.aggregator.aggregate_macro_doc(metric_name, match_results)
        for metric_name, match_results in micro_match_results.items()
    }
    macro_class_results = {
        metric_name: self.aggregator.aggregate_macro_class(
            metric_name,
            self.aggregator.bucket_by_class(results),
        )
        for metric_name, results in macro_class_match_results.items()
    }
    diagnostic_results: dict[str, Any] = {}
    if anomaly_metric.name in diagnostic_metric_names:
      diagnostic_results[anomaly_metric.name] = anomaly_metric.aggregate(anomaly_inputs)
    if any(name in diagnostic_metric_names for name in grounding_metric.metric_names):
      aggregated_grounding = grounding_metric.aggregate(grounding_inputs)
      for metric_name in diagnostic_metric_names:
        if metric_name in aggregated_grounding:
          diagnostic_results[metric_name] = aggregated_grounding[metric_name]

    return EvaluationSummary(
        dataset_info=dataset_info,
        run_info=run_info,
        micro_results=micro_results,
        macro_doc_results=macro_doc_results,
        macro_class_results=macro_class_results,
        per_doc_results=dict(per_doc_results),
        diagnostic_results=diagnostic_results,
        per_doc_diagnostic_results=dict(per_doc_diagnostic_results),
        error_buckets=self.error_analyzer.count(all_error_entries),
        error_samples=tuple(all_error_entries[:50]),
    )


class ReportInfraService:
  """Writes evaluation artifacts using the existing report writer."""

  def __init__(self) -> None:
    """Initialize the report writer."""
    self.report_writer = ReportWriter()

  def write(
      self,
      output_dir: str | Path,
      summary: EvaluationSummary,
      run_config: dict[str, Any],
      formats: list[str],
  ) -> Path:
    """Write evaluation reports to disk."""
    return self.report_writer.write(output_dir, summary, run_config, formats)

  def write_comparison(
      self,
      output_dir: str | Path,
      comparison: dict[str, Any],
      run_config: dict[str, Any],
      formats: list[str],
  ) -> Path:
    """Write comparison reports to disk."""
    return self.report_writer.write_comparison(output_dir, comparison, run_config, formats)


class GateInfraService:
  """Produces gate decisions from evaluation summaries."""

  def decide(
      self,
      summary: EvaluationSummary,
      gate_config: dict[str, Any] | None = None,
  ) -> GateDecision:
    """Produce a placeholder gate result for the current evaluation run."""
    del summary
    del gate_config
    return GateDecision(
        passed=True,
        status="pass",
        reasons=(),
        details={},
    )


class ConsoleRenderService:
  """Renders concise console-facing evaluation summaries."""

  def build_single_file_result(
      self,
      micro_results: dict[str, dict[str, Any]],
      diagnostic_results: dict[str, dict[str, Any]],
  ) -> str:
    """Render a single-file evaluation result for terminal and text output."""
    lines = ["Single File Evaluation Result"]
    for metric_name in (
        "detection_strict",
        "detection_relaxed",
        "class_strict",
        "class_relaxed",
        "structured_strict",
        "structured_relaxed",
    ):
      metric_result = micro_results[metric_name]
      lines.append(
          f"{metric_name}: "
          f"P={metric_result['precision']:.6f}, "
          f"R={metric_result['recall']:.6f}, "
          f"F1={metric_result['f1']:.6f}"
      )
    anomaly_result = diagnostic_results.get("structure_anomaly_rate")
    if anomaly_result is not None:
      lines.append(
          "structure_anomaly_rate: "
          f"{anomaly_result['value']:.6f} "
          f"({anomaly_result['numerator']}/{anomaly_result['denominator']})"
      )
    for metric_name in (
        "grounding_match_exact_rate",
        "grounding_match_lesser_rate",
        "grounding_match_fuzzy_rate",
        "grounding_match_none_rate",
    ):
      grounding_result = diagnostic_results.get(metric_name)
      if grounding_result is None:
        continue
      lines.append(
          f"{metric_name}: "
          f"{grounding_result['value']:.6f} "
          f"({grounding_result['numerator']}/{grounding_result['denominator']})"
      )
    return "\n".join(lines) + "\n"


class ConfigInfraService:
  """Loads runtime configs from YAML."""

  def __init__(self) -> None:
    """Initialize the underlying config loader."""
    self.loader = ConfigLoader()

  def load(self, config_path: str | Path) -> dict[str, Any]:
    """Load one config file."""
    return self.loader.load(config_path)


__all__ = [
    "ConfigInfraService",
    "ConsoleRenderService",
    "DatasetInfraService",
    "DomainInfraService",
    "GateInfraService",
    "MetricInfraService",
    "PredictionInfraService",
    "ReportInfraService",
    "ValidationInfraService",
]
