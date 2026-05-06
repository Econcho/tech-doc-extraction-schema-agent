"""Demo script that runs one full comparison evaluation through the top-level API."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from eval_system.api import EvaluationAPI

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "eval_system" / "configs" / "eval_all_with_compare.yaml"


def main(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
  """Run one complete comparison evaluation and print a concise summary."""
  api = EvaluationAPI()
  summary = api.run_compare_eval(config_path)
  print("Comparison evaluation finished.")
  print(f"dataset_name: {summary['dataset_info']['dataset_name']}")
  print(f"doc_count: {summary['dataset_info']['doc_count']}")
  print("regression_summary:")
  print(json.dumps(summary["regression_summary"], ensure_ascii=False, indent=2))
  print("micro_delta:")
  print(json.dumps(summary["delta_summary"]["micro_results"], ensure_ascii=False, indent=2))
  return summary


if __name__ == "__main__":
  main()
