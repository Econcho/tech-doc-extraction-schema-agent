"""Report generation utilities."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .models import EvaluationSummary


class ReportWriter:
  """Writes summary reports, per-document reports, and run snapshots to disk."""

  def write(
      self,
      output_dir: str | Path,
      summary: EvaluationSummary,
      run_config: dict[str, Any],
      formats: list[str],
  ) -> Path:
    """Write summary and per-document reports in all requested formats."""
    output_path = Path(output_dir) / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path.mkdir(parents=True, exist_ok=True)

    summary_payload = asdict(summary)
    summary_payload["gate_result"] = run_config.get("gate_result")
    summary_report_payload = self._build_summary_payload(summary_payload)
    per_doc_report_payload = self._build_per_doc_payload(summary_payload)
    if "json" in formats:
      (output_path / "summary_report.json").write_text(
          json.dumps(summary_report_payload, ensure_ascii=False, indent=2),
          encoding="utf-8",
      )
      (output_path / "per_doc_report.json").write_text(
          json.dumps(per_doc_report_payload, ensure_ascii=False, indent=2),
          encoding="utf-8",
      )
    if "markdown" in formats:
      (output_path / "summary_report.md").write_text(
          self._build_summary_markdown(summary_report_payload),
          encoding="utf-8",
      )
      (output_path / "per_doc_report.md").write_text(
          self._build_per_doc_markdown(per_doc_report_payload),
          encoding="utf-8",
      )
    (output_path / "run_config.yaml").write_text(
        yaml.safe_dump(run_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path

  def write_comparison(
      self,
      output_dir: str | Path,
      comparison: dict[str, Any],
      run_config: dict[str, Any],
      formats: list[str],
  ) -> Path:
    """Write comparison summary and per-document reports."""
    output_path = Path(output_dir) / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path.mkdir(parents=True, exist_ok=True)

    summary_payload = self._build_comparison_summary_payload(comparison)
    per_doc_payload = self._build_comparison_per_doc_payload(comparison)
    if "json" in formats:
      (output_path / "comparison_summary_report.json").write_text(
          json.dumps(summary_payload, ensure_ascii=False, indent=2),
          encoding="utf-8",
      )
      (output_path / "comparison_per_doc_report.json").write_text(
          json.dumps(per_doc_payload, ensure_ascii=False, indent=2),
          encoding="utf-8",
      )
    if "markdown" in formats:
      (output_path / "comparison_summary_report.md").write_text(
          self._build_comparison_summary_markdown(summary_payload),
          encoding="utf-8",
      )
      (output_path / "comparison_per_doc_report.md").write_text(
          self._build_comparison_per_doc_markdown(per_doc_payload),
          encoding="utf-8",
      )
    (output_path / "run_config.yaml").write_text(
        yaml.safe_dump(run_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path

  def _build_summary_payload(self, summary: dict[str, Any]) -> dict[str, Any]:
    """Build the summary-only payload without per-document sections."""
    return {
        "dataset_info": summary["dataset_info"],
        "run_info": summary["run_info"],
        "micro_results": summary["micro_results"],
        "macro_doc_results": summary["macro_doc_results"],
        "macro_class_results": summary["macro_class_results"],
        "diagnostic_results": summary["diagnostic_results"],
        "error_buckets": summary["error_buckets"],
        "error_samples": summary["error_samples"],
        "gate_result": summary.get("gate_result"),
    }

  def _build_per_doc_payload(self, summary: dict[str, Any]) -> dict[str, Any]:
    """Build the per-document payload."""
    return {
        "dataset_info": summary["dataset_info"],
        "run_info": summary["run_info"],
        "per_doc_results": summary["per_doc_results"],
        "per_doc_diagnostic_results": summary["per_doc_diagnostic_results"],
    }

  def _build_summary_markdown(self, summary: dict[str, Any]) -> str:
    """Build a comprehensive markdown summary report."""
    lines = ["# Summary Report", ""]
    lines.extend(self._build_key_value_section("Dataset", summary["dataset_info"]))
    lines.extend(self._build_key_value_section("Run", summary["run_info"]))
    lines.extend(self._build_matching_metric_section("Micro Results", summary["micro_results"]))
    lines.extend(self._build_matching_metric_section("Macro Doc Results", summary["macro_doc_results"]))
    lines.extend(self._build_macro_class_section("Macro Class Results", summary["macro_class_results"]))
    lines.extend(self._build_diagnostic_section("Diagnostic Results", summary["diagnostic_results"]))
    lines.extend(self._build_bucket_section("Error Buckets", summary["error_buckets"]))
    lines.extend(self._build_error_samples_section("Error Samples", summary.get("error_samples", [])))
    if summary.get("gate_result") is not None:
      lines.extend(self._build_key_value_section("Gate Result", summary["gate_result"]))
    lines.extend(self._build_evaluation_conclusion(summary))
    return "\n".join(lines) + "\n"

  def _build_per_doc_markdown(self, report: dict[str, Any]) -> str:
    """Build the per-document markdown report."""
    lines = ["# Per-Document Report", ""]
    lines.extend(self._build_key_value_section("Dataset", report["dataset_info"]))
    for doc_id in sorted(report["per_doc_results"]):
      lines.append(f"## {doc_id}")
      lines.append("")
      lines.extend(self._build_matching_metric_section("Matching Metrics", report["per_doc_results"][doc_id], level=3))
      diagnostic_results = report["per_doc_diagnostic_results"].get(doc_id, {})
      if diagnostic_results:
        lines.extend(self._build_diagnostic_section("Diagnostic Metrics", diagnostic_results, level=3))
    return "\n".join(lines) + "\n"

  def _build_comparison_summary_payload(self, comparison: dict[str, Any]) -> dict[str, Any]:
    """Build the comparison summary payload."""
    return {
        "dataset_info": comparison["dataset_info"],
        "compare_info": comparison["compare_info"],
        "baseline_summary": comparison["baseline_summary"],
        "candidate_summary": comparison["candidate_summary"],
        "delta_summary": comparison["delta_summary"],
        "regression_summary": comparison["regression_summary"],
    }

  def _build_comparison_per_doc_payload(self, comparison: dict[str, Any]) -> dict[str, Any]:
    """Build the comparison per-document payload."""
    return {
        "dataset_info": comparison["dataset_info"],
        "compare_info": comparison["compare_info"],
        "per_doc_comparison": comparison["per_doc_comparison"],
    }

  def _build_comparison_summary_markdown(self, comparison: dict[str, Any]) -> str:
    """Build the comparison summary markdown report."""
    lines = ["# Comparison Summary Report", ""]
    lines.extend(self._build_key_value_section("Dataset", comparison["dataset_info"]))
    lines.extend(self._build_key_value_section("Compare Info", comparison["compare_info"]))

    baseline = comparison["baseline_summary"]
    candidate = comparison["candidate_summary"]
    delta = comparison["delta_summary"]

    lines.extend(self._build_variant_summary_sections("Baseline", baseline))
    lines.extend(self._build_variant_summary_sections("Candidate", candidate))
    lines.extend(self._build_matching_delta_section("Micro Result Delta", delta["micro_results"]))
    lines.extend(self._build_matching_delta_section("Macro Doc Result Delta", delta["macro_doc_results"]))
    lines.extend(self._build_macro_class_delta_section("Macro Class Result Delta", delta.get("macro_class_results", {})))
    lines.extend(self._build_diagnostic_delta_section("Diagnostic Delta", delta.get("diagnostic_results", {})))
    lines.extend(self._build_bucket_delta_section("Error Bucket Delta", delta.get("error_buckets", {})))
    lines.extend(self._build_key_value_section("Regression Summary", comparison["regression_summary"]))
    lines.extend(self._build_comparison_conclusion(comparison))
    return "\n".join(lines) + "\n"

  def _build_comparison_per_doc_markdown(self, comparison: dict[str, Any]) -> str:
    """Build the comparison per-document markdown report."""
    lines = ["# Comparison Per-Document Report", ""]
    lines.extend(self._build_key_value_section("Dataset", comparison["dataset_info"]))
    lines.extend(self._build_key_value_section("Compare Info", comparison["compare_info"]))
    for doc_id in sorted(comparison["per_doc_comparison"]):
      doc_payload = comparison["per_doc_comparison"][doc_id]
      lines.append(f"## {doc_id}")
      lines.append("")
      lines.append("### Matching Metric Delta")
      for metric_name, metric_payload in doc_payload["matching_metrics"].items():
        baseline = metric_payload["baseline"]
        candidate = metric_payload["candidate"]
        delta = metric_payload["delta"]
        lines.append(
            f"- {metric_name}: "
            f"baseline(P={baseline['precision']:.4f}, R={baseline['recall']:.4f}, F1={baseline['f1']:.4f}), "
            f"candidate(P={candidate['precision']:.4f}, R={candidate['recall']:.4f}, F1={candidate['f1']:.4f}), "
            f"delta(ΔP={delta['precision_delta']:+.4f}, ΔR={delta['recall_delta']:+.4f}, ΔF1={delta['f1_delta']:+.4f})"
        )
      if doc_payload["diagnostic_metrics"]:
        lines.append("")
        lines.append("### Diagnostic Metric Delta")
        for metric_name, metric_payload in doc_payload["diagnostic_metrics"].items():
          lines.append(
              f"- {metric_name}: "
              f"baseline={metric_payload['baseline_value']:.4f}, "
              f"candidate={metric_payload['candidate_value']:.4f}, "
              f"delta={metric_payload['value_delta']:+.4f}"
          )
      lines.append("")
    return "\n".join(lines) + "\n"

  def _build_key_value_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a generic key-value markdown section."""
    lines = [f"{'#' * level} {title}"]
    for key, value in payload.items():
      lines.append(f"- {key}: {value}")
    lines.append("")
    return lines

  def _build_matching_metric_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for precision/recall/f1 style metrics."""
    lines = [f"{'#' * level} {title}"]
    for metric_name, metric_result in payload.items():
      lines.append(
          f"- {metric_name}: "
          f"P={metric_result['precision']:.4f}, "
          f"R={metric_result['recall']:.4f}, "
          f"F1={metric_result['f1']:.4f}"
      )
    lines.append("")
    return lines

  def _build_macro_class_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for class-level macro metrics."""
    lines = [f"{'#' * level} {title}"]
    for metric_name, class_results in payload.items():
      lines.append(f"{'#' * (level + 1)} {metric_name}")
      for extraction_class, metric_result in class_results.items():
        lines.append(
            f"- {extraction_class}: "
            f"P={metric_result['precision']:.4f}, "
            f"R={metric_result['recall']:.4f}, "
            f"F1={metric_result['f1']:.4f}"
        )
    lines.append("")
    return lines

  def _build_diagnostic_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for diagnostic metrics."""
    if not payload:
      return []
    lines = [f"{'#' * level} {title}"]
    for metric_name, metric_result in payload.items():
      lines.append(
          f"- {metric_name}: "
          f"{metric_result['value']:.4f} "
          f"({metric_result['numerator']}/{metric_result['denominator']})"
      )
    lines.append("")
    return lines

  def _build_bucket_section(
      self,
      title: str,
      payload: dict[str, int],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for error buckets."""
    lines = [f"{'#' * level} {title}"]
    for bucket, count in payload.items():
      lines.append(f"- {bucket}: {count}")
    lines.append("")
    return lines

  def _build_error_samples_section(
      self,
      title: str,
      payload: list[dict[str, Any]],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for sampled errors."""
    if not payload:
      return []
    lines = [f"{'#' * level} {title}"]
    for sample in payload:
      lines.append(
          f"- {sample['bucket']}: "
          f"doc_id={sample['doc_id']}, "
          f"pred_index={sample['pred_index']}, "
          f"gold_index={sample['gold_index']}"
      )
    lines.append("")
    return lines

  def _build_matching_delta_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for matching metric deltas."""
    lines = [f"{'#' * level} {title}"]
    for metric_name, metric_result in payload.items():
      lines.append(
          f"- {metric_name}: "
          f"baseline(P={metric_result['baseline_precision']:.4f}, R={metric_result['baseline_recall']:.4f}, F1={metric_result['baseline_f1']:.4f}), "
          f"candidate(P={metric_result['candidate_precision']:.4f}, R={metric_result['candidate_recall']:.4f}, F1={metric_result['candidate_f1']:.4f}), "
          f"delta(ΔP={metric_result['precision_delta']:+.4f}, ΔR={metric_result['recall_delta']:+.4f}, ΔF1={metric_result['f1_delta']:+.4f})"
      )
    lines.append("")
    return lines

  def _build_macro_class_delta_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for class-level delta metrics."""
    if not payload:
      return []
    lines = [f"{'#' * level} {title}"]
    for metric_name, class_results in payload.items():
      lines.append(f"{'#' * (level + 1)} {metric_name}")
      for extraction_class, metric_result in class_results.items():
        lines.append(
            f"- {extraction_class}: "
            f"baseline_F1={metric_result['baseline_f1']:.4f}, "
            f"candidate_F1={metric_result['candidate_f1']:.4f}, "
            f"ΔF1={metric_result['f1_delta']:+.4f}"
        )
    lines.append("")
    return lines

  def _build_diagnostic_delta_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for diagnostic deltas."""
    if not payload:
      return []
    lines = [f"{'#' * level} {title}"]
    for metric_name, metric_result in payload.items():
      lines.append(
          f"- {metric_name}: "
          f"baseline={metric_result['baseline_value']:.4f}, "
          f"candidate={metric_result['candidate_value']:.4f}, "
          f"delta={metric_result['value_delta']:+.4f}"
      )
    lines.append("")
    return lines

  def _build_bucket_delta_section(
      self,
      title: str,
      payload: dict[str, Any],
      *,
      level: int = 2,
  ) -> list[str]:
    """Render a section for error bucket deltas."""
    if not payload:
      return []
    lines = [f"{'#' * level} {title}"]
    for bucket_name, metric_result in payload.items():
      lines.append(
          f"- {bucket_name}: "
          f"baseline={metric_result['baseline_count']}, "
          f"candidate={metric_result['candidate_count']}, "
          f"delta={metric_result['count_delta']:+d}"
      )
    lines.append("")
    return lines

  def _build_variant_summary_sections(
      self,
      title_prefix: str,
      summary: dict[str, Any],
  ) -> list[str]:
    """Render all top-level sections for one compare variant."""
    lines: list[str] = []
    lines.extend(self._build_matching_metric_section(f"{title_prefix} Micro Results", summary["micro_results"]))
    lines.extend(self._build_matching_metric_section(f"{title_prefix} Macro Doc Results", summary["macro_doc_results"]))
    lines.extend(self._build_macro_class_section(f"{title_prefix} Macro Class Results", summary["macro_class_results"]))
    lines.extend(self._build_diagnostic_section(f"{title_prefix} Diagnostic Results", summary["diagnostic_results"]))
    lines.extend(self._build_bucket_section(f"{title_prefix} Error Buckets", summary["error_buckets"]))
    lines.extend(self._build_error_samples_section(f"{title_prefix} Error Samples", summary.get("error_samples", [])))
    return lines

  def _build_evaluation_conclusion(self, summary: dict[str, Any]) -> list[str]:
    """Build an enterprise-style evaluation conclusion."""
    lines = ["## Evaluation Conclusion", ""]
    structured_relaxed = summary["micro_results"].get("structured_relaxed", {})
    structured_strict = summary["micro_results"].get("structured_strict", {})
    anomaly = summary.get("diagnostic_results", {}).get("structure_anomaly_rate", {})
    grounding_exact = summary.get("diagnostic_results", {}).get("grounding_match_exact_rate", {})

    lines.append("### Overall Assessment")
    lines.append(
        f"- `structured_relaxed` F1={structured_relaxed.get('f1', 0.0):.4f}, "
        f"`structured_strict` F1={structured_strict.get('f1', 0.0):.4f}."
    )
    if anomaly:
      lines.append(
          f"- `structure_anomaly_rate`={anomaly['value']:.4f} "
          f"({anomaly['numerator']}/{anomaly['denominator']})."
      )
    if grounding_exact:
      lines.append(
          f"- `grounding_match_exact_rate`={grounding_exact['value']:.4f} "
          f"({grounding_exact['numerator']}/{grounding_exact['denominator']})."
      )

    lines.append("")
    lines.append("### Strengths")
    if structured_relaxed.get("f1", 0.0) >= 0.5:
      lines.append("- Structured relaxed performance is at a usable level.")
    if grounding_exact and grounding_exact["value"] >= 0.7:
      lines.append("- Grounding exact rate is high, indicating stable span alignment.")
    if anomaly and anomaly["value"] <= 0.05:
      lines.append("- Structure anomaly rate is low, indicating stable schema adherence.")
    if lines[-1] == "### Strengths":
      lines.append("- No clear strength stands out from the current report.")

    lines.append("")
    lines.append("### Key Risks")
    if structured_strict.get("f1", 0.0) < 0.4:
      lines.append("- Strict structured quality is still weak; attribute correctness remains a bottleneck.")
    if anomaly and anomaly["value"] > 0.1:
      lines.append("- Schema violations remain visible and should be reduced before production rollout.")
    top_buckets = sorted(summary["error_buckets"].items(), key=lambda item: item[1], reverse=True)[:3]
    for bucket_name, count in top_buckets:
      if count > 0:
        lines.append(f"- Error bucket `{bucket_name}` contributes {count} cases and should be analyzed.")
    if lines[-1] == "### Key Risks":
      lines.append("- No dominant risk bucket was observed in this run.")

    lines.append("")
    lines.append("### Recommended Actions")
    lines.append("- Prioritize `structured_relaxed` and `structured_strict` when iterating prompt or post-processing.")
    lines.append("- Inspect the top error buckets and sampled failures before changing schema or labels.")
    if anomaly and anomaly["value"] > 0.0:
      lines.append("- Reduce structure anomalies before optimizing downstream matching metrics.")
    lines.append("")
    return lines

  def _build_comparison_conclusion(self, comparison: dict[str, Any]) -> list[str]:
    """Build an enterprise-style comparison conclusion."""
    lines = ["## Comparison Conclusion", ""]
    regression_summary = comparison["regression_summary"]
    structured_delta = comparison["delta_summary"]["micro_results"].get("structured_relaxed", {})
    strict_delta = comparison["delta_summary"]["micro_results"].get("structured_strict", {})
    anomaly_delta = comparison["delta_summary"]["diagnostic_results"].get("structure_anomaly_rate", {})

    lines.append("### Overall Assessment")
    lines.append(f"- {regression_summary['overall_assessment']}.")
    lines.append(f"- {regression_summary['core_metric_assessment']}.")
    lines.append(
        f"- Improved metrics: {regression_summary['improved_metric_count']}, "
        f"degraded metrics: {regression_summary['degraded_metric_count']}, "
        f"unchanged metrics: {regression_summary['unchanged_metric_count']}."
    )
    lines.append(
        f"- `structured_relaxed` micro ΔF1={structured_delta.get('f1_delta', 0.0):+.4f}, "
        f"`structured_strict` micro ΔF1={strict_delta.get('f1_delta', 0.0):+.4f}."
    )
    if anomaly_delta:
      lines.append(
          f"- `structure_anomaly_rate` Δ={anomaly_delta['value_delta']:+.4f}; "
          "lower is better for this metric."
      )

    lines.append("")
    lines.append("### Interpretation")
    if structured_delta.get("f1_delta", 0.0) > 0 and strict_delta.get("f1_delta", 0.0) >= 0:
      lines.append("- Candidate improves the core structured metrics and is directionally better than baseline.")
    elif structured_delta.get("f1_delta", 0.0) < 0 or strict_delta.get("f1_delta", 0.0) < 0:
      lines.append("- Candidate introduces regression on core structured metrics and should not replace baseline directly.")
    else:
      lines.append("- Candidate changes are limited; the current evidence does not show a decisive quality shift.")

    lines.append("")
    lines.append("### Recommended Actions")
    lines.append("- Review per-document delta to locate where gains or regressions concentrate.")
    lines.append("- Check macro class delta to identify which extraction classes drive the overall result.")
    lines.append("- Use error bucket delta to determine whether changes affect recall, precision, class, or attribute behavior.")
    lines.append("")
    return lines
