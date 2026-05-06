import json
import os
from pathlib import Path

import langextract as lx
from langextract.chunk_policies.structured_kep import KEPStructuredChunkPolicy
from langextract.providers.funhpc import FunHPCDeepseekLanguageModel
from langextract.providers.openai import OpenAILanguageModel

from prompt.KEP_examples_v2 import examples as KEP_examples
from tools.json_tools import extraction2json


PROMPT_PATH = Path("prompt/md/KEP_prompt_v2.md")
OUTPUT_SUFFIX = "dsflash-chunk1000-structured-all_heading"
REGISTRY_PATH = Path("eval_system/dataset/KEP/registry_all.json")
DATASET_ROOT = REGISTRY_PATH.parent

prompt = PROMPT_PATH.read_text(encoding="utf-8")
examples = KEP_examples
prompt_filename = PROMPT_PATH.stem

model = OpenAILanguageModel(
    model_id="deepseek-v4-flash",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
# model = FunHPCDeepseekLanguageModel(
#     model_id="deepseek-v3.2",
#     api_key="YOUR_FUNHPC_API_KEY",
# )
chunk_policy = KEPStructuredChunkPolicy()

registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
entries = [entry for entry in registry["entries"] if entry.get("enabled", True)]

for entry in entries:
    kep_dirname = entry["doc_id"]
    document_path = DATASET_ROOT / entry["document_path"]
    input_text = document_path.read_text(encoding="utf-8")

    output_filename = f"pred_{kep_dirname}"
    if OUTPUT_SUFFIX:
        output_filename = f"{output_filename}_{OUTPUT_SUFFIX}"
    output_path = (
        Path("result")
        / prompt_filename
        / kep_dirname
        / f"{output_filename}.json"
    )

    result = lx.extract(
        text_or_documents=input_text,
        prompt_description=prompt,
        examples=examples,
        model=model,
        fence_output=True,
        use_schema_constraints=False,
        extraction_passes=1,
        max_workers=1,
        max_char_buffer=1000,
        chunk_policy=chunk_policy,
    )

    print(f"=== {kep_dirname} extractions ===")
    extraction2json(result.extractions, output_path)
    for i, ex in enumerate(result.extractions):
        print(f"[{i}]")
        print("class:", ex.extraction_class)
        print("text:", ex.extraction_text)
        print("attributes:", ex.attributes)
        print("char_interval:", getattr(ex, "char_interval", None))
        print("token_interval:", getattr(ex, "token_interval", None))
        print("alignment_status:", getattr(ex, "alignment_status", None))
