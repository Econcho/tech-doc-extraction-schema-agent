# 指标说明

本文档介绍 `eval_system` 当前支持的全部评测指标，包括：

- 指标计算方式
- 指标含义
- 典型用途

当前指标分为两类：

1. 主评测指标
2. 诊断指标

## 1. 主评测指标

主评测指标使用 gold 和 prediction 做一对一匹配，并计算：

- Precision
- Recall
- F1

### 1.1 `detection_strict`

计算方式：

- 只比较 `extraction_text`
- 使用严格文本匹配
- 忽略 `extraction_class`
- 忽略 `attributes`

用途：

- 衡量模型是否把应抽取的文本片段“原样抓到”
- 适合先看文本检测能力，不看类别和结构

### 1.2 `detection_relaxed`

计算方式：

- 只比较 `extraction_text`
- 使用 relaxed 文本匹配
- 忽略 `extraction_class`
- 忽略 `attributes`

用途：

- 衡量模型是否至少抓到了接近的文本
- 适合看召回趋势和宽松文本定位能力

### 1.3 `class_strict`

计算方式：

- 要求 `extraction_class` 一致
- `extraction_text` 使用严格匹配
- 忽略 `attributes`

用途：

- 衡量文本抓取正确且类别判断正确的能力
- 适合看“文本 + 类别”的联合质量

### 1.4 `class_relaxed`

计算方式：

- 要求 `extraction_class` 一致
- `extraction_text` 使用 relaxed 匹配
- 忽略 `attributes`

用途：

- 在文本允许近似的情况下评估类别判断能力
- 适合看类别层面的总体质量趋势

### 1.5 `structured_strict`

计算方式：

- 要求 `extraction_class` 一致
- `extraction_text` 严格匹配
- `attributes` 严格匹配

用途：

- 衡量完整结构化抽取质量
- 这是最严格、最接近“最终可用性”的主指标之一

### 1.6 `structured_relaxed`

计算方式：

- 要求 `extraction_class` 一致
- `extraction_text` relaxed 匹配
- `attributes` 仍然严格匹配

用途：

- 衡量在文本允许一定松弛时，结构化抽取整体是否正确
- 这是当前非常重要的综合质量指标

## 2. 诊断指标

诊断指标不参与 TP / FP / FN 一对一匹配，它们主要用于帮助分析 prediction 的结构质量和 grounding 质量。

### 2.1 `structure_anomaly_rate`

计算方式：

- 对一个 prediction 文件，设 extraction 总数为 `N`
- 结构异常的 extraction 数量为 `m`
- 指标值为：
  `m / N`

结构异常的定义：

- `extraction_class` 不在 schema 中
- 或者 class 合法，但 `attributes` 中出现非法字段
- 或者属性值落在非法枚举值上

用途：

- 衡量 prediction 自身的 schema 合规程度
- 适合检查 prompt、后处理、结构输出是否稳定
- 越低越好

### 2.2 `grounding_match_exact_rate`

计算方式：

- 对一个 prediction 文件，设 extraction 总数为 `N`
- `alignment_status == "match_exact"` 的 extraction 数量为 `m`
- 指标值为：
  `m / N`

用途：

- 衡量 prediction 中有多少抽取结果是精确 grounding 的
- 越高越好

### 2.3 `grounding_match_lesser_rate`

计算方式：

- `alignment_status == "match_lesser"` 的比例

用途：

- 衡量轻度不精确 grounding 的占比
- 一般用于辅助看 grounding 质量分布

### 2.4 `grounding_match_fuzzy_rate`

计算方式：

- `alignment_status == "match_fuzzy"` 的比例

用途：

- 衡量模糊 grounding 的比例
- 越低通常越好

### 2.5 `grounding_match_none_rate`

计算方式：

- `alignment_status is None` 的比例
- 也包括无法识别状态时归入 `none`

用途：

- 衡量没有 grounding 信息或 grounding 失败的比例
- 越低通常越好

## 3. 指标之间的关系

可以把这 11 个指标理解成三个层次：

### 文本检测层

- `detection_strict`
- `detection_relaxed`

回答：

- 模型有没有把相关文本抓出来

### 类别判断层

- `class_strict`
- `class_relaxed`

回答：

- 抓出来的文本类别对不对

### 完整结构层

- `structured_strict`
- `structured_relaxed`

回答：

- 文本、类别、属性整体对不对

### 结构与 grounding 诊断层

- `structure_anomaly_rate`
- `grounding_match_exact_rate`
- `grounding_match_lesser_rate`
- `grounding_match_fuzzy_rate`
- `grounding_match_none_rate`

回答：

- prediction 的结构有没有异常
- grounding 的质量分布怎样

## 4. 如何使用这些指标

### 看总体抽取质量

优先关注：

- `structured_relaxed`
- `structured_strict`

### 看文本抓取能力

优先关注：

- `detection_relaxed`
- `detection_strict`

### 看类别判断能力

优先关注：

- `class_relaxed`
- `class_strict`

### 看 prediction 结构稳定性

优先关注：

- `structure_anomaly_rate`

### 看 grounding 质量

优先关注：

- `grounding_match_exact_rate`
- `grounding_match_none_rate`

## 5. 指标配置方式

当前 YAML 配置中的 `metrics` 可以直接写所有指标名，例如：

```yaml
metrics:
  - detection_strict
  - detection_relaxed
  - class_strict
  - class_relaxed
  - structured_strict
  - structured_relaxed
  - structure_anomaly_rate
  - grounding_match_exact_rate
  - grounding_match_lesser_rate
  - grounding_match_fuzzy_rate
  - grounding_match_none_rate
```

其中：

- 前 6 个是主评测指标
- 后 5 个是诊断指标

## 6. 一个实用判断原则

如果你要判断一个新参数是否“整体更好”，通常建议优先看：

1. `structured_relaxed`
2. `structured_strict`
3. `class_relaxed`
4. `structure_anomaly_rate`
5. `grounding_match_exact_rate`

原因是：

- `structured_*` 最接近最终结构化抽取可用性
- `structure_anomaly_rate` 能暴露 schema 输出问题
- `grounding_match_exact_rate` 能反映抽取结果和原文的对齐质量
