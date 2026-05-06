# API 层说明

`api` 是 `eval_system` 的对外入口层。它的职责不是实现评测逻辑，而是把外部调用稳定地转发给 `pipeline`。

当前 API 层的核心目标是：

- 提供统一、稳定的调用入口
- 隔离外部使用方式和内部实现细节
- 保持 CLI 和 Python API 的行为一致

## 1. 目录结构

```text
api/
├─ README.md
├─ __init__.py
├─ facade.py
└─ cli.py
```

- [`facade.py`](/F:/LLM/langextract-main/eval_system/api/facade.py)
  高层 API 门面。
- [`cli.py`](/F:/LLM/langextract-main/eval_system/api/cli.py)
  命令行入口。

## 2. API 层的职责边界

### API 应该做的事

- 暴露稳定方法名
- 统一外部调用语义
- 转发请求给正确的 pipeline
- 保持 CLI 和 Python API 的调用习惯一致

### API 不应该做的事

- 直接读取注册表
- 直接加载 gold / pred
- 直接实现匹配和指标计算
- 直接实现报告写出
- 直接承载业务编排细节

这些都属于：

- `pipeline`
- `infra`

## 3. API 层和其他层的关系

```text
外部调用
  ->
API
  ->
Pipeline
  ->
Infra
```

可以把它理解成：

- `api`
  回答“外部应该怎么调用系统”
- `pipeline`
  回答“这次请求应该走哪条流程”
- `infra`
  回答“底层能力怎么执行”

## 4. 现有 API 组件说明

### 4.1 `EvaluationAPI`

位置：

- [`facade.py`](/F:/LLM/langextract-main/eval_system/api/facade.py)

这是当前推荐的高层 API 门面。

它内部持有三条 pipeline：

- `FinalEvaluationPipeline`
- `ValidationPipeline`
- `SingleFileEvaluationPipeline`

对外暴露的方法：

- `run_final_eval(config_path)`
  跑一次完整评测。
- `validate_dataset(config_path)`
  只校验 gold 数据集。
- `validate_prediction(config_path)`
  只校验 prediction。
- `run_single_file_eval(gold_path, pred_path, ...)`
  跑单文件评测。

### 4.2 `EvaluationRunner`

`EvaluationRunner` 现在不再是单独文件中的独立实现，而是在
[`__init__.py`](/F:/LLM/langextract-main/eval_system/api/__init__.py)
中作为 `EvaluationAPI` 的别名导出。

也就是说：

- `EvaluationAPI`
  是实际实现
- `EvaluationRunner`
  是兼容名称

保留这个名字的原因只是兼容已有脚本调用习惯，例如：

```python
from eval_system.api import EvaluationRunner
```

但内部并不存在第二套逻辑。

### 4.3 CLI

位置：

- [`cli.py`](/F:/LLM/langextract-main/eval_system/api/cli.py)

当前 CLI 提供 3 个命令：

- `run`
- `validate-dataset`
- `validate-pred`

CLI 的实现方式也很简单：

1. 解析命令行参数
2. 初始化 `EvaluationAPI`
3. 调用对应 API 方法
4. 打印 JSON 结果

也就是说，CLI 只是 API 的命令行包装，不承担额外业务逻辑。

## 5. 现有 API 的功能和调用链

下面分别说明每个入口。

### 5.1 `EvaluationAPI.run_final_eval`

功能：

- 执行一次完整评测

调用链：

1. 外部调用 `EvaluationAPI.run_final_eval(config_path)`
2. API 转发到：
   [`FinalEvaluationPipeline.run()`](/F:/LLM/langextract-main/eval_system/pipeline/final_eval.py)
3. pipeline 再调用：
   - `ConfigInfraService`
   - `DatasetInfraService`
   - `DomainInfraService`
   - `ValidationInfraService`
   - `PredictionInfraService`
   - `MetricInfraService`
   - `ReportInfraService`
   - `GateInfraService`
4. 返回序列化后的 summary

### 5.2 `EvaluationAPI.validate_dataset`

功能：

- 只校验 gold 数据集

调用链：

1. 外部调用 `EvaluationAPI.validate_dataset(config_path)`
2. API 转发到：
   [`ValidationPipeline.validate_dataset()`](/F:/LLM/langextract-main/eval_system/pipeline/validation.py)
3. pipeline 再调用：
   - `ConfigInfraService`
   - `DatasetInfraService`
   - `ValidationInfraService`
4. 返回错误列表

### 5.3 `EvaluationAPI.validate_prediction`

功能：

- 只校验 prediction

调用链：

1. 外部调用 `EvaluationAPI.validate_prediction(config_path)`
2. API 转发到：
   [`ValidationPipeline.validate_prediction()`](/F:/LLM/langextract-main/eval_system/pipeline/validation.py)
3. pipeline 再调用：
   - `ConfigInfraService`
   - `DomainInfraService`
   - `DatasetInfraService`
   - `PredictionInfraService`
   - `ValidationInfraService`
4. 返回错误列表

### 5.4 `EvaluationAPI.run_single_file_eval`

功能：

- 对单个 gold 文件和 prediction 文件做快速评测

调用链：

1. 外部调用 `EvaluationAPI.run_single_file_eval(...)`
2. API 转发到：
   [`SingleFileEvaluationPipeline.run()`](/F:/LLM/langextract-main/eval_system/pipeline/single_file_eval.py)
3. pipeline 再调用：
   - `DatasetInfraService`
   - `DomainInfraService`
   - `PredictionInfraService`
   - `ValidationInfraService`
   - `MetricInfraService`
   - `ConsoleRenderService`
   - `GateInfraService`
4. 打印控制台结果，并返回序列化后的 summary

## 6. Python API 使用方式

### 使用 `EvaluationAPI`

```python
from eval_system.api import EvaluationAPI

api = EvaluationAPI()

summary = api.run_final_eval("eval_system/configs/eval_kep_v1.yaml")
dataset_errors = api.validate_dataset("eval_system/configs/eval_kep_v1.yaml")
pred_errors = api.validate_prediction("eval_system/configs/eval_kep_v1.yaml")
single = api.run_single_file_eval(
    "eval_system/dataset/KEP/labels/sig-apps/19-Graduate-CronJob-to-Stable/label_v2.json",
    "result/KEP_prompt_v2/19-Graduate-CronJob-to-Stable/pred_19-Graduate-CronJob-to-Stable_dschat-chunk1000.json",
)
```

### 使用 `EvaluationRunner`

```python
from eval_system.api import EvaluationRunner

runner = EvaluationRunner()

summary = runner.run("eval_system/configs/eval_kep_v1.yaml")
dataset_errors = runner.validate_dataset("eval_system/configs/eval_kep_v1.yaml")
pred_errors = runner.validate_prediction("eval_system/configs/eval_kep_v1.yaml")
single = runner.evaluate_paths(
    "eval_system/dataset/KEP/labels/sig-apps/19-Graduate-CronJob-to-Stable/label_v2.json",
    "result/KEP_prompt_v2/19-Graduate-CronJob-to-Stable/pred_19-Graduate-CronJob-to-Stable_dschat-chunk1000.json",
)
```

## 7. CLI 使用方式

运行完整评测：

```bash
python -m eval_system.api.cli run --config eval_system/configs/eval_kep_v1.yaml
```

只校验 gold：

```bash
python -m eval_system.api.cli validate-dataset --config eval_system/configs/eval_kep_v1.yaml
```

只校验 prediction：

```bash
python -m eval_system.api.cli validate-pred --config eval_system/configs/eval_kep_v1.yaml
```

## 8. 如何新增一个新的 API 方法

如果后续要新增一个新的外部能力，例如：

- `run_compare_eval`
- `run_ablation_eval`
- `run_targeted_eval`

推荐步骤如下。

### 第一步：先在 `pipeline` 里实现流程

不要直接在 API 层写逻辑。应先新增对应 pipeline，例如：

- `CompareEvaluationPipeline`

### 第二步：在 `EvaluationAPI.__init__()` 注入新 pipeline

例如：

```python
self.compare_eval = CompareEvaluationPipeline()
```

### 第三步：在 `EvaluationAPI` 暴露一个稳定方法

例如：

```python
def run_compare_eval(self, baseline_config: str | Path, candidate_config: str | Path) -> dict[str, Any]:
  return self.compare_eval.run(baseline_config, candidate_config)
```

### 第四步：如有需要，再同步到兼容别名和 CLI

如果这个能力需要兼容旧脚本或需要命令行支持，再补：

- `api/__init__.py` 中的别名导出
- `cli.py`

## 9. 设计建议

### API 应保持薄而稳定

API 层越薄越好。理想状态是：

- 只做入口转换
- 不做业务逻辑堆积

### 方法名应直接表达用户意图

推荐 API 方法名聚焦“用户要干什么”，例如：

- `run_final_eval`
- `validate_prediction`
- `run_single_file_eval`

而不是暴露底层实现名词。

### 不要让 API 依赖底层过多细节

例如 API 不应该开始知道：

- registry JSON 结构细节
- metric registry 细节
- matcher 细节
- threshold 内部数学

这些都会导致 API 层变得脆弱。

## 10. 当前 API 层的定位总结

当前 `api` 层已经形成了比较清晰的结构：

- `EvaluationAPI`
  稳定高层门面
- `EvaluationRunner`
  `EvaluationAPI` 的兼容名称
- `CLI`
  命令行包装

它们共同特点是：

- 不直接承载评测算法
- 不直接承载数据组织逻辑
- 只把外部请求准确转发给 pipeline

这也是后续继续扩展 compare、ablation、targeted 等评测流程时最稳的方式。 
