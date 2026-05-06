# Proposal Agent

MVP workflow:

1. Ingest triage conclusions into proposal signals and buckets:

```bash
python -m residual_info_agents.proposal_pipeline.ingest_triage_results \
  --residual_info_json residual_info_agents/data/blocks_ignore_testcase.json
```

2. Inspect allowed proposal buckets or run a known bucket:

```bash
python -m residual_info_agents.proposal_agent.run --bucket_id bucket_xxx
```

The implementation uses a deterministic local hash embedding and stores vectors
in Milvus. Start Milvus separately and configure `embedding.milvus` in
`config.yaml` before running ingestion.
