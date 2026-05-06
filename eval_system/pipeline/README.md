# Pipeline 层说明

`pipeline` 是 `eval_system` 的流程编排层。它的职责不是实现底层匹配、指标和数据加载，而是把 `infra` 里的能力按顺序组装成一条可执行的评测流程。

当前 `pipeline` 的定位是：

- 接收来自 `api` 的高层请求
- 调用 `infra` 完成数据加载、校验、评测、报告
- 返回统一的结果对象或序列化结果

## 1. 目录结构

```text
pipeline/
├─ README.md
├─ __init__.py
├─ final_eval.py
├─ single_file_eval.py
└─ validation.py
```

- [`final_eval.py`](/F:/LLM/langextract-main/eval_system/pipeline/final_eval.py)
  完整评测流程。
- [`single_file_eval.py`](/F:/LLM/langextract-main/eval_system/pipeline/single_file_eval.py)
  单文件便捷评测流程。
- [`validation.py`](/F:/LLM/langextract-main/eval_system/pipeline/validation.py)
  只做校验，不做评分。

## 2. Pipeline 层的边界

### Pipeline 应该做的事

- 读取和整理输入参数
- 决定一条流程需要调用哪些 `infra service`
- 决定执行顺序
- 组装中间结果
- 返回最终结果

### Pipeline 不应该做的事

- 直接实现匹配规则
- 直接实现指标计算
- 直接解析注册表
- 直接操作底层 adapter 细节
- 直接实现报告格式细节

这些能力都应留在 `infra`。

## 3. 组装一个新 Pipeline 的详细教程

下面给出一个从零组装新 pipeline 的推荐步骤。这个过程适合后续新增：

- compare pipeline
- ablation pipeline
- targeted eval pipeline
- regression pipeline

### 第一步：先定义这个 pipeline 的目标

先明确这个 pipeline 回答什么问题。

例如：

- “跑一整套注册表评测”
- “只校验 prediction 是否合规”
- “对两个参数做回归对比”
- “只评测某一类文档”

只有目标清晰，后面才能判断要调用哪些 `infra service`。

### 第二步：列出需要的 Infra Service

当前可直接复用的服务主要在 [`services.py`](/F:/LLM/langextract-main/eval_system/infra/services.py)：

- `ConfigInfraService`
- `DatasetInfraService`
- `DomainInfraService`
- `PredictionInfraService`
- `ValidationInfraService`
- `MetricInfraService`
- `ReportInfraService`
- `ConsoleRenderService`
- `GateInfraService`

你应该只依赖 service，而不是在 pipeline 里再去拼底层模块。

常见组合：

- 完整评测：
  `Config -> Domain -> Validation -> Dataset -> Prediction -> Metric -> Gate -> Report`
- 单文件评测：
  `Domain -> Dataset(single) -> Prediction(single) -> Validation -> Metric -> Console`
- 校验：
  `Config -> Dataset / Prediction -> Validation`

### 第三步：写 `__init__`，初始化所需的 service

推荐写法和现有 pipeline 保持一致：

```python
class MyPipeline:
  def __init__(self) -> None:
    self.configs = ConfigInfraService()
    self.datasets = DatasetInfraService()
    self.domains = DomainInfraService()
    self.validation = ValidationInfraService()
    self.predictions = PredictionInfraService()
    self.metrics = MetricInfraService()
```

只初始化当前流程真正需要的 service，不要无意义全量注入。

### 第四步：在 `run()` 里只做流程编排

推荐结构：

1. 读取输入
2. 加载 plugin
3. 构建 context
4. 校验配置
5. 加载 gold
6. 加载 pred
7. 校验 pred
8. 运行指标
9. 生成报告或控制台输出
10. 返回结果

推荐伪代码：

```python
def run(self, config_path: str | Path) -> dict[str, Any]:
  config = self.configs.load(config_path)
  plugin = self.domains.load_plugin(config["domain_plugin"])
  context = plugin.build_context(config.get("thresholds", {}))

  self.validation.raise_if_errors(
      self.validation.validate_config(config, config["report"]["output_dir"])
  )

  gold_docs, dataset_info = self.datasets.load_dataset(config["dataset"])
  pred_docs = self.predictions.load_predictions(config, dataset_info, gold_docs)

  self.validation.raise_if_errors(
      self.validation.validate_prediction(
          pred_docs,
          known_doc_ids=set(gold_docs.keys()),
          allowed_classes=set(plugin.get_allowed_classes()),
          allowed_attribute_keys=set(plugin.get_allowed_attribute_keys()),
          class_attribute_schema=plugin.get_class_attribute_schema(),
      )
  )

  registry = self.domains.build_metric_registry(plugin)
  summary = self.metrics.evaluate_documents(
      gold_docs=gold_docs,
      pred_docs=pred_docs,
      plugin=plugin,
      context=context,
      metric_names=config["metrics"],
      dataset_info=dataset_info,
      run_info={...},
      registry=registry,
  )

  return ...
```

### 第五步：决定输出形式

当前 pipeline 常见输出方式有两种：

1. 返回序列化后的字典
2. 打印控制台摘要并可选落盘

推荐原则：

- 面向程序调用的 pipeline：返回字典
- 面向人工查看的便捷流程：额外输出 console text

### 第六步：只在 Pipeline 里做“流程决策”

一个新 pipeline 最容易写坏的地方，是把底层逻辑重新写一遍。应避免这些做法：

- 在 pipeline 里直接写指标数学
- 在 pipeline 里直接读 JSON 注册表
- 在 pipeline 里直接构建 `EvalExtraction`
- 在 pipeline 里直接写 markdown 报告

如果你发现自己在做这些事，通常说明该逻辑应该下沉到 `infra`。

### 第七步：必要时抽取序列化辅助方法

如果 pipeline 需要把 `EvaluationSummary` 转成普通字典，可以像现有实现一样保留一个私有方法：

- `_serialize_summary()`

这种方法可以留在 pipeline 层，因为它属于“结果交付形式”，不属于底层数学逻辑。

## 4. 现有 Pipeline 的功能和调用链

下面按文件说明。

### 4.1 `FinalEvaluationPipeline`

位置：

- [`final_eval.py`](/F:/LLM/langextract-main/eval_system/pipeline/final_eval.py)

功能：

- 从配置文件启动一次完整评测
- 加载注册表定义的 gold 子集
- 加载 prediction
- 做 prediction 校验
- 计算主指标与诊断指标
- 输出报告
- 返回序列化结果

调用的 `infra service`：

- `ConfigInfraService`
- `DatasetInfraService`
- `DomainInfraService`
- `ValidationInfraService`
- `PredictionInfraService`
- `MetricInfraService`
- `ReportInfraService`
- `GateInfraService`

详细调用链：

1. `self.configs.load(config_path)`
   读取 YAML 配置。
2. `self.domains.load_plugin(config["domain_plugin"])`
   加载领域插件。
3. `plugin.build_context(config.get("thresholds", {}))`
   构建匹配上下文和阈值上下文。
4. `self.validation.validate_config(...)`
   校验配置合法性。
5. `self.datasets.load_dataset(config["dataset"])`
   读取注册表，加载 gold 文档。
6. `self.predictions.load_predictions(config, dataset_info, gold_docs)`
   读取 prediction 文件或目录。
7. `self.validation.validate_prediction(...)`
   宽松校验 prediction 结构。
8. `self.domains.build_metric_registry(plugin)`
   构建主指标注册表。
9. `self.metrics.evaluate_documents(...)`
   执行指标计算、诊断指标、聚合、错误分析。
10. `self.gates.decide(summary, config.get("gate"))`
    生成 gate 结果。
11. `self.reports.write(...)`
    输出 JSON / Markdown 报告。
12. `_serialize_summary(summary)`
    返回普通字典。

### 4.2 `SingleFileEvaluationPipeline`

位置：

- [`single_file_eval.py`](/F:/LLM/langextract-main/eval_system/pipeline/single_file_eval.py)

功能：

- 对一个 gold 文件和一个 prediction 文件做快速评测
- 控制台打印 6 个主指标和诊断指标
- 可选把控制台结果保存为 txt

调用的 `infra service`：

- `DatasetInfraService`
- `DomainInfraService`
- `ValidationInfraService`
- `PredictionInfraService`
- `MetricInfraService`
- `ConsoleRenderService`
- `GateInfraService`

详细调用链：

1. `self.domains.load_plugin("kep_v1")`
   直接固定加载 KEP 插件。
2. `plugin.build_context({})`
   构建默认阈值上下文。
3. `self.datasets.load_single_gold(...)`
   读取单个 gold 文件并推导 `doc_id`。
4. `self.predictions.load_single_prediction(...)`
   读取单个 prediction 文件。
5. `self.validation.validate_prediction(...)`
   校验 prediction。
6. `self.domains.build_metric_registry(plugin)`
   构建默认主指标。
7. `self.metrics.evaluate_documents(...)`
   跑完整评分逻辑，但对象只有一篇文档。
8. `self.gates.decide(summary)`
   生成 gate 结果。
9. `_serialize_summary(summary)`
   转换成普通字典。
10. `self.console.build_single_file_result(...)`
    渲染控制台文本。
11. `print(console_output)`
    打印结果。
12. 如果 `save_result=True`
    调用 `_resolve_output_path(...)` 决定保存路径并落盘。

适用场景：

- 本地快速看一篇文档的抽取质量
- 调 prompt 或模型参数时快速做 spot check

### 4.3 `ValidationPipeline`

位置：

- [`validation.py`](/F:/LLM/langextract-main/eval_system/pipeline/validation.py)

功能：

- 只校验，不评分
- 支持：
  - `validate_dataset`
  - `validate_prediction`

调用的 `infra service`：

- `ConfigInfraService`
- `DatasetInfraService`
- `DomainInfraService`
- `PredictionInfraService`
- `ValidationInfraService`

详细调用链一：`validate_dataset()`

1. `self.configs.load(config_path)`
   读取配置。
2. `self.datasets.load_dataset(config["dataset"])`
   通过注册表加载 gold 数据。
3. `self.validation.validate_dataset(list(gold_docs.values()))`
   校验 gold 数据集合。
4. 返回错误字典列表。

详细调用链二：`validate_prediction()`

1. `self.configs.load(config_path)`
   读取配置。
2. `self.domains.load_plugin(config["domain_plugin"])`
   加载领域插件。
3. `self.datasets.load_dataset(config["dataset"])`
   通过注册表加载 gold。
4. `self.predictions.load_predictions(config, dataset_info, gold_docs)`
   加载 prediction。
5. `self.validation.validate_prediction(...)`
   校验 prediction。
6. 返回错误字典列表。

适用场景：

- 先检查数据和 prediction 是否可评测
- 在正式评测前做预检查

## 5. 现有 Pipeline 和 Infra 的对应关系

可以把当前关系概括成下面这张表：

| Pipeline | 目标 | 主要调用的 Infra Service |
| --- | --- | --- |
| `FinalEvaluationPipeline` | 完整评测 | Config, Dataset, Domain, Validation, Prediction, Metric, Report, Gate |
| `SingleFileEvaluationPipeline` | 单文件快速评测 | Dataset, Domain, Validation, Prediction, Metric, Console, Gate |
| `ValidationPipeline` | 只做校验 | Config, Dataset, Domain, Prediction, Validation |

## 6. 新增 Pipeline 时的推荐结构模板

推荐直接按下面这个结构新建文件：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..infra.services import (
    ConfigInfraService,
    DatasetInfraService,
    DomainInfraService,
    ValidationInfraService,
    PredictionInfraService,
    MetricInfraService,
)


class MyPipeline:
  """Describe one pipeline clearly."""

  def __init__(self) -> None:
    """Initialize only the services this pipeline needs."""
    self.configs = ConfigInfraService()
    self.datasets = DatasetInfraService()
    self.domains = DomainInfraService()
    self.validation = ValidationInfraService()
    self.predictions = PredictionInfraService()
    self.metrics = MetricInfraService()

  def run(self, config_path: str | Path) -> dict[str, Any]:
    """Orchestrate one complete custom pipeline."""
    config = self.configs.load(config_path)
    plugin = self.domains.load_plugin(config["domain_plugin"])
    context = plugin.build_context(config.get("thresholds", {}))
    gold_docs, dataset_info = self.datasets.load_dataset(config["dataset"])
    pred_docs = self.predictions.load_predictions(config, dataset_info, gold_docs)
    self.validation.raise_if_errors(
        self.validation.validate_prediction(
            pred_docs,
            known_doc_ids=set(gold_docs.keys()),
            allowed_classes=set(plugin.get_allowed_classes()),
            allowed_attribute_keys=set(plugin.get_allowed_attribute_keys()),
            class_attribute_schema=plugin.get_class_attribute_schema(),
        )
    )
    registry = self.domains.build_metric_registry(plugin)
    summary = self.metrics.evaluate_documents(
        gold_docs=gold_docs,
        pred_docs=pred_docs,
        plugin=plugin,
        context=context,
        metric_names=config["metrics"],
        dataset_info=dataset_info,
        run_info={},
        registry=registry,
    )
    return {"summary": summary}
```

## 7. 设计上的注意事项

### 不要让 Pipeline 重新实现 Infra

如果一个 pipeline 开始出现下面这些行为，就说明设计在变坏：

- 直接 `json.loads()` 注册表
- 直接遍历 raw prediction 字典
- 直接实现 TP / FP / FN
- 直接拼 markdown 报告

这些都应该放回 `infra`。

### Pipeline 可以不同，但输入输出契约最好稳定

建议新 pipeline 尽量保持：

- 输入参数风格一致
- 返回字典结构尽量兼容已有 summary
- 错误处理方式一致

这样 `api` 层才能稳定复用。

### 先抽象流程，再抽象复用

如果后续出现：

- compare pipeline
- ablation pipeline
- targeted eval pipeline

不要一开始就做过度抽象。先让每个 pipeline 明确工作，再考虑把公共步骤提成辅助方法或更细的 orchestration helper。

## 8. 当前建议的后续 Pipeline

在现有基础上，最值得新增的几条 pipeline 是：

- Compare / Regression Pipeline
  对 baseline 和 candidate 做差异评测。
- Ablation Pipeline
  对不同参数配置批量对比。
- Targeted Eval Pipeline
  只评某些 `doc_type`、某些 registry 子集或某些类。

这些都可以直接复用当前 `infra`，不需要推翻现有结构。 
