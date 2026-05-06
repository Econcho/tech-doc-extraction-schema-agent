import os
from pathlib import Path

import langextract as lx
from langextract.chunk_policies.structured_kep import KEPStructuredChunkPolicy
from langextract.providers.openai import OpenAILanguageModel
from langextract.providers.funhpc import FunHPCDeepseekLanguageModel
from langextract.runtime_observer import RuntimeObserverConfig

from prompt.KEP_examples_v2 import examples as KEP_examples
from tools.json_tools import extraction2json


PROMPT_PATH = Path("prompt/md/KEP_prompt_v2.md")
KEP_DIRNAME = "19-Graduate-CronJob-to-Stable"
OUTPUT_SUFFIX = "dsflash-chunk1000-test"
REPO_ROOT = Path(__file__).resolve().parent
RUNTIME_OBSERVER_CONFIG_PATH = (
    REPO_ROOT
    / "langextract"
    / "runtime_observer"
    / "config"
    / "runtime_observer_config.json"
)


prompt = PROMPT_PATH.read_text(encoding="utf-8")

examples = KEP_examples

kep_dir = Path("docs/dev/KEP") / KEP_DIRNAME
input_text = (kep_dir / "README.md").read_text(encoding="utf-8")

prompt_filename = PROMPT_PATH.stem
output_filename = f"pred_{KEP_DIRNAME}"
if OUTPUT_SUFFIX:
    output_filename = f"{output_filename}_{OUTPUT_SUFFIX}"
output_path = Path("result") / prompt_filename / f"{output_filename}.json"

model = OpenAILanguageModel(
    model_id="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# model = FunHPCDeepseekLanguageModel(
#     model_id="deepseek-v3.2",
#     api_key="IfRgHQT9pAAghINfLMdsScos7JfwRqFkkhBxdZ7Sq9KOvSxQ",
# )

chunk_policy = KEPStructuredChunkPolicy()
runtime_observer_config = None
if RUNTIME_OBSERVER_CONFIG_PATH.exists():
    runtime_observer_config = RuntimeObserverConfig.from_file(
        RUNTIME_OBSERVER_CONFIG_PATH
    )
    if not Path(runtime_observer_config.output_dir).is_absolute():
        runtime_observer_config.output_dir = str(
            REPO_ROOT / runtime_observer_config.output_dir
        )
    print(f"runtime observer config: {RUNTIME_OBSERVER_CONFIG_PATH}")
    print(f"runtime observer output_dir: {runtime_observer_config.output_dir}")
else:
    print(f"runtime observer config not found: {RUNTIME_OBSERVER_CONFIG_PATH}")

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
    runtime_observer_config=runtime_observer_config,
)

print("=== extractions ===")
extraction2json(result.extractions, output_path)
for i, ex in enumerate(result.extractions):
    print(f"[{i}]")
    print("class:", ex.extraction_class)
    print("text:", ex.extraction_text)
    print("attributes:", ex.attributes)
    print("char_interval:", getattr(ex, "char_interval", None))
    print("token_interval:", getattr(ex, "token_interval", None))
    print("alignment_status:", getattr(ex, "alignment_status", None))
