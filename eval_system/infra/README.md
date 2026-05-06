# Infra 层说明

`infra` 是 `eval_system` 的基础设施层，负责承载评测系统的底层能力。它不直接决定“跑哪个流程”，也不负责对外 API，而是为 `pipeline` 和 `api` 提供稳定的基础组件。

当前 `infra` 已经完全采用注册表驱动的数据组织，不再支持旧版 `manifest/split` 数据集模式。

## 1. 目录结构

```text
infra/
├─ README.md
├─ __init__.py
├─ models.py
├─ services.py
├─ adapters/
├─ core/
├─ datasets/
├─ domains/
├─ metrics/
└─ registry/
```

## 2. 模块职责

### `services.py`

Infra 对上层暴露的服务层，主要包括：

- `ConfigInfraService`
  读取运行配置。
- `DatasetInfraService`
  通过注册表加载 gold 数据集。
- `PredictionInfraService`
  读取 prediction 文件并交给 adapter 转换。
- `DomainInfraService`
  加载领域插件并构建指标注册表。
- `MetricInfraService`
  运行匹配、评分、聚合、诊断指标。
- `ValidationInfraService`
  执行配置、数据、prediction 校验。
- `ReportInfraService`
  输出 JSON / Markdown 报告。
- `ConsoleRenderService`
  生成控制台摘要文本。
- `GateInfraService`
  预留的门禁决策服务。

### `models.py`

保存 Infra 层对外暴露的辅助模型，例如门禁结果对象。

### `adapters/`

负责把外部 prediction 格式转换为统一内部对象：

- `LangExtractAdapter`
- `JsonAdapter`

它们的输出目标都是 `EvalDocument` 和 `EvalExtraction`。

### `core/`

评测核心能力，包含：

- `models.py`
  评测核心数据模型。
- `matching.py`
  一对一匹配逻辑。
- `aggregation.py`
  micro / macro 聚合逻辑。
- `normalizers.py`
  文本归一化与分词辅助。
- `error_buckets.py`
  错误分桶分析。
- `report.py`
  报告写出。
- `validation.py`
  配置与 prediction 校验。
- `config.py`
  YAML 配置读取。

### `datasets/`

负责 gold 数据加载。当前只保留一个入口：

- `DatasetLoader.load_registry()`

也就是说，`infra/datasets` 现在只接受注册表驱动的数据集组织。

### `domains/`

负责领域规则封装。当前主要是：

- `KepDomainPlugin`

该层定义：

- 支持的 `extraction_class`
- class 对应属性 schema
- 属性值约束
- 文本匹配上下文

### `metrics/`

负责评测指标与诊断指标，包括：

- 主指标
  - `detection_strict`
  - `detection_relaxed`
  - `class_strict`
  - `class_relaxed`
  - `structured_strict`
  - `structured_relaxed`
- 诊断指标
  - `structure_anomaly_rate`
  - `grounding_match_exact_rate`
  - `grounding_match_lesser_rate`
  - `grounding_match_fuzzy_rate`
  - `grounding_match_none_rate`

### `registry/`

注册系统，负责定义评测子集并向评测运行提供条目列表。主要模块：

- `models.py`
  注册表与注册条目数据模型。
- `loader.py`
  从 JSON 读取注册表。
- `service.py`
  对外提供加载、列条目、路径解析等接口。
- `builder.py`
  从文档目录和标注目录生成注册表。

详细使用方式见 [`infra/registry/README.md`](/F:/LLM/langextract-main/eval_system/infra/registry/README.md)。

## 3. 与上层的边界

### Infra 不负责

- 决定外部调用方式
- 编排完整业务流程
- 定义 CLI 命令语义

这些职责属于：

- `api/`
- `pipeline/`

### Infra 负责

- 提供可复用的底层能力
- 保持评测运行时的数据和逻辑一致性
- 为上层流程提供稳定接口

## 4. 当前数据入口原则

当前 Infra 层的数据入口原则很简单：

- gold 数据只从注册表读取
- prediction 数据只从配置指定路径读取
- 不再支持基于 `manifest.yaml` 或 `split.txt` 的旧版数据组织

因此，如果上层配置没有提供：

```yaml
dataset:
  registry_path: ...
```

`DatasetInfraService` 会直接报错。

## 5. 后续扩展建议

如果后续要扩展系统：

- 新增 prediction 格式：改 `adapters/`
- 新增领域：改 `domains/`
- 新增指标：改 `metrics/`
- 新增 gold 加载来源：优先扩展注册系统或在 `datasets/` 新增新的注册表消费方式

不建议重新引入目录扫描式或 split 文件式的数据入口，否则会破坏当前注册表驱动的统一性。 
