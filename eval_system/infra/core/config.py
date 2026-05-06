"""Config loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
  """Loads YAML runtime configs for the evaluation system."""

  def load(self, config_path: str | Path) -> dict[str, Any]:
    """Load one YAML config file into a Python dictionary."""
    path = Path(config_path).resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
      raise ValueError("Config file must load into a mapping.")
    return self._resolve_paths(payload, path.parent)

  def _resolve_paths(self, config: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Resolve known relative paths against the config file directory."""
    project_root = base_dir.parent.parent
    dataset = config.get("dataset")
    if isinstance(dataset, dict) and dataset.get("registry_path"):
      dataset["registry_path"] = str(
          self._resolve_one_path(dataset["registry_path"], base_dir, project_root)
      )

    prediction = config.get("prediction")
    if isinstance(prediction, dict) and prediction.get("path"):
      prediction["path"] = str(
          self._resolve_one_path(prediction["path"], base_dir, project_root)
      )
    baseline = config.get("baseline")
    if isinstance(baseline, dict) and baseline.get("path"):
      baseline["path"] = str(
          self._resolve_one_path(baseline["path"], base_dir, project_root)
      )
    candidate = config.get("candidate")
    if isinstance(candidate, dict) and candidate.get("path"):
      candidate["path"] = str(
          self._resolve_one_path(candidate["path"], base_dir, project_root)
      )

    report = config.get("report")
    if isinstance(report, dict) and report.get("output_dir"):
      report["output_dir"] = str(
          self._resolve_one_path(report["output_dir"], base_dir, project_root)
      )

    config["__config_path__"] = str(base_dir)
    return config

  def _resolve_one_path(self, raw_path: str | Path, base_dir: Path, project_root: Path) -> Path:
    """Resolve one path value relative to the config file directory."""
    path = Path(raw_path)
    if path.is_absolute():
      return path
    project_candidate = (project_root / path).resolve()
    config_candidate = (base_dir / path).resolve()
    if project_candidate.exists() or not config_candidate.exists():
      return project_candidate
    return config_candidate
