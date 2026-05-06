"""Demo script that runs one single-file evaluation through the top-level API."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from eval_system.api import EvaluationAPI

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "eval_system" / "configs" / "eval_single_file.yaml"


def main(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
  """Run one single-file evaluation and print a concise summary."""
  config = _load_config(config_path)
  api = EvaluationAPI()
  summary = api.run_single_file_eval(
      config["gold_path"],
      config["pred_path"],
      save_result=config.get("save_result", False),
      save_path=config.get("save_path"),
  )
  print("Single-file evaluation finished.")
  print(f"gold_path: {config['gold_path']}")
  print(f"pred_path: {config['pred_path']}")
  print("micro_results:")
  print(json.dumps(summary["micro_results"], ensure_ascii=False, indent=2))
  print("diagnostic_results:")
  print(json.dumps(summary["diagnostic_results"], ensure_ascii=False, indent=2))
  return summary


def _load_config(config_path: str | Path) -> dict:
  """Load one single-file demo config and resolve relative paths from project root."""
  path = Path(config_path)
  payload = yaml.safe_load(path.read_text(encoding="utf-8"))
  for key in ("gold_path", "pred_path", "save_path"):
    value = payload.get(key)
    if not value:
      continue
    resolved = PROJECT_ROOT / value if not Path(value).is_absolute() else Path(value)
    payload[key] = str(resolved)
  return payload


if __name__ == "__main__":
  main()
