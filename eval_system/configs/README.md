# 配置文件教程

本目录用于存放 `eval_system` 的运行配置文件。当前配置格式为 YAML，完整评测、校验流程都通过配置文件驱动。

当前示例配置见：

- [`eval_kep_v1.yaml`](/F:/LLM/langextract-main/eval_system/configs/eval_kep_v1.yaml)

## 1. 配置文件的作用

一个配置文件负责描述一次评测运行至少需要的这些信息：

- 使用哪个注册表定义 gold 数据集
- prediction 文件或目录在哪里
- 使用哪个领域插件
- 使用哪些指标
- 报告输出到哪里

## 2. 最小可用配置

当前一份最小可用配置如下：

```yaml
dataset:
  registry_path: eval_system/dataset/KEP/registry_all.json

prediction:
  path: result/KEP_prompt_v1/pred_0000-kep-process.json
  format: json
  adapter: langextract
  doc_id: 0000-kep-process

domain_plugin: kep_v1

matcher:
  type: max_weight_bipartite

metrics:
  - detection_strict
  - detection_relaxed
  - class_strict
  - class_relaxed
  - structured_strict
  - structured_relaxed

report:
  output_dir: eval_system/reports/example_run
  formats:
    - json
    - markdown
```

## 3. 顶层字段说明

当前配置文件的顶层字段中：

### 必须字段

- `dataset`
- `prediction`
- `domain_plugin`
- `matcher`
- `metrics`
- `report`

这些字段缺少任意一个，配置校验会失败。

### 可选字段

- `thresholds`
- `gate`

说明：

- `thresholds`
  用于覆盖 relaxed match 的阈值。
- `gate`
  目前是预留扩展位，系统会接收，但当前默认 gate 逻辑较轻。

## 4. `dataset` 字段

### 作用

指定这次评测所使用的 gold 数据集入口。

### 必须字段

- `registry_path`

### 配置示例

```yaml
dataset:
  registry_path: eval_system/dataset/KEP/registry_all.json
```

### 字段说明

- `registry_path`
  注册表文件路径。评测系统会从这个注册表中读取所有 `enabled=true` 的条目，并据此加载文档和 label。

### 当前限制

- 当前系统只支持注册表驱动
- 不再支持 `manifest.yaml`
- 不再支持 `split.txt`
- 不再支持旧版 `dataset.path + dataset.split` 模式

## 5. `prediction` 字段

### 作用

指定 prediction 输入来源。

### 必须字段

- `path`
- `adapter`

### 常用字段

- `format`
- `doc_id`
- `doc_subdir`
- `filename_template`

### 配置示例

```yaml
prediction:
  path: result/KEP_prompt_v2
  format: json
  adapter: langextract
  doc_subdir: true
  filename_template: pred_{doc_id}_dschat-chunk1000.json
```

### 字段说明

- `path`
  prediction 文件路径或 prediction 目录路径。

- `adapter`
  prediction 读取适配器。当前支持：
  - `langextract`
  - `json`

- `format`
  当前更像说明性字段，主要用于增强配置可读性。系统当前真正依赖的是 `adapter`。

- `doc_id`
  当 `prediction.path` 指向单个 prediction 文件时，建议显式提供。

- `doc_subdir`
  目录模式下是否先进入 `prediction.path/<doc_id>/` 再找文件。当前你的多文档结果目录就是这种结构。

- `filename_template`
  目录模式下每篇文档的 prediction 文件名模板。支持 `{doc_id}` 占位符。
  例如：
  `pred_{doc_id}_dschat-chunk1000.json`

### 目录模式说明

如果 `prediction.path` 指向一个目录，系统会按以下规则查找每篇文档对应的 prediction 文件：

1. 如果 `doc_subdir=true`，先进入：
   `prediction.path/<doc_id>/`
2. 如果提供了 `filename_template`，使用：
   `filename_template.format(doc_id=doc_id)`
3. 否则默认使用：
   `<doc_id>.json`

例如当前 KEP 多文档评测可写成：

```yaml
prediction:
  path: result/KEP_prompt_v2
  adapter: langextract
  doc_subdir: true
  filename_template: pred_{doc_id}_dschat-chunk1000.json
```

## 6. `domain_plugin` 字段

### 作用

指定当前评测所使用的领域规则。

### 必须字段

- `domain_plugin`

### 配置示例

```yaml
domain_plugin: kep_v1
```

### 当前支持值

- `kep_v1`

### 说明

领域插件负责提供：

- 允许的 `extraction_class`
- class 对应属性 schema
- relaxed 匹配上下文
- 默认指标集合

## 7. `matcher` 字段

### 作用

描述本次评测使用的匹配器类型。

### 必须字段

- `type`

### 配置示例

```yaml
matcher:
  type: max_weight_bipartite
```

### 当前支持值

- `max_weight_bipartite`

### 说明

当前系统实际使用的是最大权重二分图一对一匹配。

## 8. `metrics` 字段

### 作用

指定这次评测要计算哪些主指标。

### 必须字段

- `metrics`

### 配置示例

```yaml
metrics:
  - detection_strict
  - detection_relaxed
  - class_strict
  - class_relaxed
  - structured_strict
  - structured_relaxed
```

### 当前可用指标

- `detection_strict`
- `detection_relaxed`
- `class_strict`
- `class_relaxed`
- `structured_strict`
- `structured_relaxed`
- `structure_anomaly_rate`
- `grounding_match_exact_rate`
- `grounding_match_lesser_rate`
- `grounding_match_fuzzy_rate`
- `grounding_match_none_rate`

### 说明

这些指标现在都可以直接写进 `metrics`。其中：

- 前 6 个是主评测指标
- 后 5 个是诊断指标

## 9. `thresholds` 字段

### 作用

覆盖 relaxed match 所使用的阈值。

### 可选字段

- `text_relaxed_f1`
- `lccs_ratio`
- `substring_precision`
- `substring_recall`

### 配置示例

```yaml
thresholds:
  text_relaxed_f1: 0.8
  lccs_ratio: 0.7
  substring_precision: 0.8
  substring_recall: 0.8
```

### 当前约束

所有 `thresholds` 中的值都必须在 `0` 到 `1` 之间，否则配置校验失败。

### 不写时的行为

如果不写，系统会使用领域插件的默认阈值上下文。

## 10. `report` 字段

### 作用

指定评测结果的输出位置和格式。

### 必须字段

- `output_dir`

### 常用字段

- `formats`

### 配置示例

```yaml
report:
  output_dir: eval_system/reports/example_run
  formats:
    - json
    - markdown
```

### 字段说明

- `output_dir`
  报告输出根目录。配置校验时会尝试创建该目录；真正的报告会写入其下的时间戳子目录，避免后一次运行覆盖前一次结果。

- `formats`
  报告输出格式列表。当前常用值：
  - `json`
  - `markdown`

### 当前报告文件

每次运行会在时间戳目录下输出：

- `summary_report.json`
- `summary_report.md`
- `per_doc_report.json`
- `per_doc_report.md`
- `run_config.yaml`

### 不写 `formats` 时的行为

如果没有显式提供，系统默认使用：

```yaml
formats:
  - json
  - markdown
```

## 11. `gate` 字段

### 作用

为后续门禁策略预留配置入口。

### 当前状态

- 可选
- 当前系统接收该字段
- 当前默认 gate 实现较轻，主要返回占位式结果

### 建议

如果当前没有门禁需求，可以不写。

## 12. 路径解析规则

当前配置加载器会自动解析这些路径字段：

- `dataset.registry_path`
- `prediction.path`
- `report.output_dir`

### 解析规则

1. 如果是绝对路径，直接使用
2. 如果是相对路径，优先按项目根目录解析
3. 如果项目根目录下不存在，再回退到配置文件所在目录解析

因此，像下面这种写法是推荐的：

```yaml
dataset:
  registry_path: eval_system/dataset/KEP/registry_all.json

prediction:
  path: result/KEP_prompt_v2/19-Graduate-CronJob-to-Stable/pred_19-Graduate-CronJob-to-Stable_dschat-chunk1000.json

report:
  output_dir: eval_system/reports/example_run
```

## 13. 配置文件使用方式

### Python API

```python
from eval_system.api import EvaluationAPI

api = EvaluationAPI()
summary = api.run_final_eval("eval_system/configs/eval_kep_v1.yaml")
```

### CLI

```bash
python -m eval_system.api.cli run --config eval_system/configs/eval_kep_v1.yaml
```

### 只做校验

```bash
python -m eval_system.api.cli validate-dataset --config eval_system/configs/eval_kep_v1.yaml
python -m eval_system.api.cli validate-pred --config eval_system/configs/eval_kep_v1.yaml
```

## 14. 常见错误

### 1. 缺少顶层必须字段

例如缺少：

- `dataset`
- `prediction`
- `report`

会直接触发配置校验错误。

### 2. `dataset.registry_path` 不存在

这会导致 gold 数据加载失败。

### 3. `thresholds` 超出范围

例如：

```yaml
thresholds:
  text_relaxed_f1: 1.2
```

会触发配置校验失败，因为阈值必须在 `0` 到 `1` 之间。

### 4. `prediction.path` 指向错误位置

会导致 prediction 加载失败，或导致没有可评测的 prediction 文档。

### 5. 目录模式和真实文件布局不匹配

例如实际文件是：

```text
result/KEP_prompt_v2/19-Graduate-CronJob-to-Stable/pred_19-Graduate-CronJob-to-Stable_dschat-chunk1000.json
```

但配置里没有写：

- `doc_subdir: true`
- `filename_template: pred_{doc_id}_dschat-chunk1000.json`

就会导致系统找不到 prediction 文件。

## 15. 推荐实践

- 一个实验版本对应一份独立配置文件
- 路径尽量写成项目根目录相对路径
- `report.output_dir` 按实验名称分目录
- 修改 `metrics` 和 `thresholds` 时，最好保留一份基线配置做对比

## 16. 建议的配置命名方式

推荐命名模式：

```text
eval_<domain>_<version>.yaml
```

例如：

- `eval_kep_v1.yaml`
- `eval_kep_chunk1000.yaml`
- `eval_kep_structured_ft.yaml`

这样更适合后续做参数对比和批量实验管理。 
