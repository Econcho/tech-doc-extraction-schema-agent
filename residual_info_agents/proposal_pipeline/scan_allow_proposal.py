from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual_info_agents.proposal_pipeline.proposal_trigger import (
    get_allow_proposal_buckets,
)
from residual_info_agents.proposal_pipeline.signal_ingestion import load_config


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--config", default="residual_info_agents/proposal_agent/config.yaml"
  )
  args = parser.parse_args()
  bucket_ids = get_allow_proposal_buckets(load_config(Path(args.config)))
  print(json.dumps({"allow_proposal_buckets": bucket_ids}, indent=2))


if __name__ == "__main__":
  main()
