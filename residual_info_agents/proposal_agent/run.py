from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual_info_agents.proposal_agent.proposal_agent import ProposalAgent


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--bucket_id", required=True)
  parser.add_argument(
      "--schema_description",
      default="residual_info_agents/data/KEP_schema_v2.json",
  )
  parser.add_argument(
      "--config",
      default="residual_info_agents/proposal_agent/config.yaml",
  )
  parser.add_argument(
      "--tools",
      default="residual_info_agents/proposal_agent/TOOLS.json",
  )
  args = parser.parse_args()

  agent = ProposalAgent(config=Path(args.config), tools=Path(args.tools))
  result = agent.main_loop(args.bucket_id, args.schema_description)
  print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
  main()
