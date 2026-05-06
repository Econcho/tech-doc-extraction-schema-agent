# 注册表驱动评测系统架构

## 1. 总体目标

当前 `eval_system` 采用三层架构：

- `api`
- `pipeline`
- `infra`

同时，数据组织已经完全切换为注册表驱动：

- 不再支持 `manifest.yaml`
- 不再支持 `split.txt`
- 不再支持通过旧版数据集根目录推导评测集合

评测子集由注册表文件显式定义。

## 2. 顶层目录

```text
eval_system/
├─ api/
├─ pipeline/
├─ infra/
├─ dataset/
│  └─ KEP/
│     ├─ docs/
│     ├─ labels/
│     └─ registry_all.json
├─ configs/
├─ README.md
└─ ARCHITECTURE.md
```

## 3. 三层职责

### API

位置：

- [`api/facade.py`](/F:/LLM/langextract-main/eval_system/api/facade.py)
- [`api/cli.py`](/F:/LLM/langextract-main/eval_system/api/cli.py)

职责：

- 对外暴露稳定调用接口
- 把外部调用转发给 pipeline
- 保持 CLI 和 Python API 一致
- 通过 `EvaluationRunner = EvaluationAPI` 兼容旧名称

### Pipeline

位置：

- [`pipeline/final_eval.py`](/F:/LLM/langextract-main/eval_system/pipeline/final_eval.py)
- [`pipeline/single_file_eval.py`](/F:/LLM/langextract-main/eval_system/pipeline/single_file_eval.py)
- [`pipeline/validation.py`](/F:/LLM/langextract-main/eval_system/pipeline/validation.py)

职责：

- 组织完整评测流程
- 组织单文件评测流程
- 组织配置、数据、prediction 校验流程

### Infra

位置：

- [`infra/services.py`](/F:/LLM/langextract-main/eval_system/infra/services.py)
- [`infra/core/`](/F:/LLM/langextract-main/eval_system/infra/core)
- [`infra/adapters/`](/F:/LLM/langextract-main/eval_system/infra/adapters)
- [`infra/datasets/`](/F:/LLM/langextract-main/eval_system/infra/datasets)
- [`infra/domains/`](/F:/LLM/langextract-main/eval_system/infra/domains)
- [`infra/metrics/`](/F:/LLM/langextract-main/eval_system/infra/metrics)
- [`infra/registry/`](/F:/LLM/langextract-main/eval_system/infra/registry)

职责：

- 数据模型
- 注册表读取
- gold / pred 加载
- 匹配
- 指标计算
- 聚合
- 诊断指标
- 报告输出

## 4. 注册表驱动链路

### 输入

运行配置必须提供：

```yaml
dataset:
  registry_path: eval_system/dataset/KEP/registry_all.json
```

### 流程

1. `EvaluationAPI` 进入对应 pipeline。
2. pipeline 调用 `DatasetInfraService.load_dataset()`。
3. `DatasetInfraService` 强制读取 `dataset.registry_path`。
4. `DatasetLoader.load_registry()` 通过 `RegistryService` 加载注册表。
5. `RegistryService` 返回所有 `enabled=true` 的条目。
6. 对每个条目读取：
   - `document_path`
   - `label_path`
7. 组装 `gold_docs: dict[str, EvalDocument]`。
8. `PredictionInfraService` 加载 prediction。
9. `MetricInfraService` 计算主指标与诊断指标。
10. `ReportInfraService` 输出结果。

## 5. 当前评测产出

主指标：

- `detection_strict`
- `detection_relaxed`
- `class_strict`
- `class_relaxed`
- `structured_strict`
- `structured_relaxed`

诊断指标：

- `structure_anomaly_rate`
- `grounding_match_exact_rate`
- `grounding_match_lesser_rate`
- `grounding_match_fuzzy_rate`
- `grounding_match_none_rate`

聚合结果：

- `micro_results`
- `macro_doc_results`
- `macro_class_results`
- `per_doc_results`
- `diagnostic_results`
- `per_doc_diagnostic_results`

## 6. 当前架构约束

- 评测系统只接受注册表驱动的数据入口。
- `dataset` 目录中的原始文档和 label 是数据资产，不由评测代码动态生成。
- 注册表是 `<KEP 文档和 label>` 与 `<评测运行>` 之间的桥梁。
- 一个注册表文件代表一个独立评测子集。

## 7. 扩展方向

后续如果要扩展：

- 新文档类型：复用 `infra/registry` 和 `infra/datasets`
- 新指标：扩展 `infra/metrics`
- 新聚合维度：扩展 `infra/core/aggregation.py`
- 新 pipeline：放到 `pipeline/`
- 新 API：放到 `api/`

当前架构的核心原则是：数据入口只认注册表，评测流程只消费注册条目。这样可以避免旧版目录扫描和 split 管理带来的耦合。 
