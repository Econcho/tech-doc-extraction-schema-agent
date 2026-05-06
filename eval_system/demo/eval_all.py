"""Demo script that runs one full evaluation through the top-level API."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from eval_system.api import EvaluationAPI

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "eval_system" / "configs" / "eval_all_without_compare.yaml"


def main(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
  """Run one complete evaluation and print a concise summary."""
  api = EvaluationAPI()
  summary = api.run_final_eval(config_path)
  print("Final evaluation finished.")
  print(f"dataset_name: {summary['dataset_info']['dataset_name']}")
  print(f"doc_count: {summary['dataset_info']['doc_count']}")
  print("micro_results:")
  print(json.dumps(summary["micro_results"], ensure_ascii=False, indent=2))
  print("diagnostic_results:")
  print(json.dumps(summary["diagnostic_results"], ensure_ascii=False, indent=2))
  return summary


if __name__ == "__main__":
  main()
