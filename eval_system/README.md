# Eval System

`eval_system` 是当前项目的结构化抽取评测系统。它已经统一为三层架构，并且只采用注册表驱动的数据组织方式。

当前系统解决三类问题：

- 定义“哪些文档参与评测”
- 对 gold 和 prediction 进行结构化抽取质量评测
- 输出主指标、诊断指标、错误分析和报告

## 1. 快速导航

如果你第一次进入这个目录，建议按下面顺序阅读：

1. [`README.md`](README.md)
   总导航、总体架构和快速使用说明。
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
   系统整体架构说明。
3. [`metrics.md`](metrics.md)
   为什么采用 `api / pipeline / infra` 三层结构。
4. [`api/README.md`](api/README.md)
   API 层入口和调用方式。
5. [`pipeline/README.md`](pipeline/README.md)
   Pipeline 组装方式和现有调用链。
6. [`infra/README.md`](infra/README.md)
   Infra 层模块构成和底层能力。
7. [`infra/registry/README.md`](infra/registry/README.md)
   注册系统说明。

## 2. 当前目录结构

```text
eval_system/
├─ README.md
├─ ARCHITECTURE.md
├─ 三层架构说明.md
├─ api/
├─ pipeline/
├─ infra/
├─ dataset/
│  └─ KEP/
│     ├─ docs/
│     ├─ labels/
│     └─ registry_all.json
└─ configs/
```

各层职责：

- `api/`
  对外稳定入口。负责 Python API、兼容式 runner、CLI。
- `pipeline/`
  流程编排层。负责把多个 infra service 组装成完整评测流程。
- `infra/`
  基础设施层。负责注册表、数据加载、匹配、指标、聚合、报告。
- `dataset/`
  数据资产目录。当前 KEP 数据集包含原文、label 和注册表。

## 3. 整体架构

当前系统采用三层结构：

```text
外部调用
  ->
API
  ->
Pipeline
  ->
Infra
```

这三层的关系是：

- `api`
  回答“外部怎么调用”
- `pipeline`
  回答“这次流程怎么组织”
- `infra`
  回答“底层能力怎么执行”

数据入口已经统一为注册表驱动：

- 不再支持 `manifest.yaml`
- 不再支持 `split.txt`
- 不再支持旧版目录扫描式数据发现

评测子集由注册表显式定义，一个注册表文件就是一个独立评测子集。

## 4. 数据组织方式

当前 KEP 数据集目录：

```text
eval_system/dataset/KEP/
├─ docs/
├─ labels/
└─ registry_all.json
```

含义：

- `docs/`
  KEP 原文档。
- `labels/`
  结构化抽取标注文件。
- `registry_all.json`
  注册表，定义当前哪些 KEP 条目参与评测。

评测运行不会扫描整个目录，而是只读取注册表中的条目。

## 5. 当前支持的评测能力

### 主指标

- `detection_strict`
- `detection_relaxed`
- `class_strict`
- `class_relaxed`
- `structured_strict`
- `structured_relaxed`

### 诊断指标

- `structure_anomaly_rate`
- `grounding_match_exact_rate`
- `grounding_match_lesser_rate`
- `grounding_match_fuzzy_rate`
- `grounding_match_none_rate`

### 结果输出

当前评测结果可包含：

- `micro_results`
- `macro_doc_results`
- `macro_class_results`
- `per_doc_results`
- `diagnostic_results`
- `per_doc_diagnostic_results`
- `error_buckets`
- `error_samples`

## 6. 最小使用方式

### 6.1 配置文件

当前配置必须包含注册表入口：

```yaml
dataset:
  registry_path: eval_system/dataset/KEP/registry_all.json
```

完整示例见 [`eval_kep_v1.yaml`](/F:/LLM/langextract-main/eval_system/configs/eval_kep_v1.yaml)。

### 6.2 Python API

完整评测：

```python
from eval_system.api import EvaluationRunner

runner = EvaluationRunner()
summary = runner.run("eval_system/configs/eval_kep_v1.yaml")
```

单文件评测：

```python
from eval_system.api import EvaluationRunner

runner = EvaluationRunner()
summary = runner.evaluate_paths(
    "eval_system/dataset/KEP/labels/sig-apps/19-Graduate-CronJob-to-Stable/label_v2.json",
    "result/KEP_prompt_v2/19-Graduate-CronJob-to-Stable/pred_19-Graduate-CronJob-to-Stable_dschat-chunk1000.json",
)
```

### 6.3 CLI

完整评测：

```bash
python -m eval_system.api.cli run --config eval_system/configs/eval_kep_v1.yaml
```

校验数据集：

```bash
python -m eval_system.api.cli validate-dataset --config eval_system/configs/eval_kep_v1.yaml
```

校验 prediction：

```bash
python -m eval_system.api.cli validate-pred --config eval_system/configs/eval_kep_v1.yaml
```

## 7. 当前主调用链

完整评测的调用链可以概括为：

1. `api` 接收请求
2. `pipeline` 读取配置并选择流程
3. `infra/registry` 读取注册表
4. `infra/datasets` 加载 gold
5. `infra/adapters` 加载 pred
6. `infra/metrics` 计算主指标和诊断指标
7. `infra/core` 做匹配、聚合、错误分析
8. `infra/report` 输出报告

如果你要看每一层的细节：

- API 调用链见 [`api/README.md`](/F:/LLM/langextract-main/eval_system/api/README.md)
- Pipeline 调用链见 [`pipeline/README.md`](/F:/LLM/langextract-main/eval_system/pipeline/README.md)
- Infra 组成见 [`infra/README.md`](/F:/LLM/langextract-main/eval_system/infra/README.md)

## 8. 如何继续扩展

推荐扩展方向：

- 新指标：改 `infra/metrics`
- 新领域：改 `infra/domains`
- 新注册表或新文档类型：改 `infra/registry`
- 新评测流程：改 `pipeline`
- 新入口或新命令：改 `api`

不建议再引入旧版 `manifest/split` 数据组织，否则会破坏当前注册表驱动的一致性。

## 9. 相关文档索引

- 总体架构：
  [`ARCHITECTURE.md`](/F:/LLM/langextract-main/eval_system/ARCHITECTURE.md)
- 三层架构原则：
  [`三层架构说明.md`](/F:/LLM/langextract-main/eval_system/三层架构说明.md)
- API 层：
  [`api/README.md`](/F:/LLM/langextract-main/eval_system/api/README.md)
- Pipeline 层：
  [`pipeline/README.md`](/F:/LLM/langextract-main/eval_system/pipeline/README.md)
- Infra 层：
  [`infra/README.md`](/F:/LLM/langextract-main/eval_system/infra/README.md)
- 注册系统：
  [`infra/registry/README.md`](/F:/LLM/langextract-main/eval_system/infra/registry/README.md)
