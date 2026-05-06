from __future__ import annotations

import argparse
from pathlib import Path

from residual_info_agents.proposal_pipeline.signal_builder import SignalBuilder
from residual_info_agents.proposal_pipeline.signal_ingestion import SignalIngestion
from residual_info_agents.proposal_pipeline.signal_ingestion import load_config
from residual_info_agents.proposal_pipeline.triage_result_loader import (
    TriageResultLoader,
)
from residual_info_agents.proposal_pipeline.triage_result_loader import (
    default_conclusion_path,
)


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--config", default="residual_info_agents/proposal_agent/config.yaml")
  parser.add_argument("--residual_info_json", required=True)
  parser.add_argument("--conclusion_json", default=str(default_conclusion_path()))
  args = parser.parse_args()

  config = load_config(Path(args.config))
  conclusions = TriageResultLoader().load(args.conclusion_json)
  signals = SignalBuilder().build_from_files(args.residual_info_json, conclusions)
  mappings = SignalIngestion(config).ingest(signals)
  print(f"Ingested {len(mappings)} proposal signals.")


if __name__ == "__main__":
  main()
