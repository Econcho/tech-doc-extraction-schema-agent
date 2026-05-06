"""Command-line entry points exposed from the top-level API layer."""

from __future__ import annotations

import argparse
import json

from .facade import EvaluationAPI


def build_parser() -> argparse.ArgumentParser:
  """Build the top-level CLI parser."""
  parser = argparse.ArgumentParser(prog="evalx")
  subparsers = parser.add_subparsers(dest="command", required=True)

  compare_parser = subparsers.add_parser("compare")
  compare_parser.add_argument("--config", required=True)

  run_parser = subparsers.add_parser("run")
  run_parser.add_argument("--config", required=True)

  dataset_parser = subparsers.add_parser("validate-dataset")
  dataset_parser.add_argument("--config", required=True)

  pred_parser = subparsers.add_parser("validate-pred")
  pred_parser.add_argument("--config", required=True)
  return parser


def main() -> None:
  """Execute the requested CLI command."""
  args = build_parser().parse_args()
  api = EvaluationAPI()

  if args.command == "compare":
    summary = api.run_compare_eval(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
  elif args.command == "run":
    summary = api.run_final_eval(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
  elif args.command == "validate-dataset":
    errors = api.validate_dataset(args.config)
    print(json.dumps(errors, ensure_ascii=False, indent=2))
  elif args.command == "validate-pred":
    errors = api.validate_prediction(args.config)
    print(json.dumps(errors, ensure_ascii=False, indent=2))


if __name__ == "__main__":
  main()
