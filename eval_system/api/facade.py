"""Top-level stable API facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..pipeline.compare_eval import CompareEvaluationPipeline
from ..pipeline.final_eval import FinalEvaluationPipeline
from ..pipeline.single_file_eval import SingleFileEvaluationPipeline
from ..pipeline.validation import ValidationPipeline


class EvaluationAPI:
  """Exposes stable high-level evaluation operations."""

  def __init__(self) -> None:
    """Initialize the pipelines used by the public API."""
    self.compare_eval = CompareEvaluationPipeline()
    self.final_eval = FinalEvaluationPipeline()
    self.validation = ValidationPipeline()
    self.single_file_eval = SingleFileEvaluationPipeline()

  def run_compare_eval(self, config_path: str | Path) -> dict[str, Any]:
    """Run one config-driven baseline-vs-candidate comparison evaluation."""
    return self.compare_eval.run(config_path)

  def run_final_eval(self, config_path: str | Path) -> dict[str, Any]:
    """Run one config-driven final evaluation."""
    return self.final_eval.run(config_path)

  def validate_dataset(self, config_path: str | Path) -> list[dict[str, str]]:
    """Validate one configured dataset."""
    return self.validation.validate_dataset(config_path)

  def validate_prediction(self, config_path: str | Path) -> list[dict[str, str]]:
    """Validate one configured prediction set."""
    return self.validation.validate_prediction(config_path)

  def run_single_file_eval(
      self,
      gold_path: str | Path,
      pred_path: str | Path,
      *,
      save_result: bool = False,
      save_path: str | Path | None = None,
  ) -> dict[str, Any]:
    """Run the single-file evaluation workflow."""
    return self.single_file_eval.run(
        gold_path,
        pred_path,
        save_result=save_result,
        save_path=save_path,
    )
