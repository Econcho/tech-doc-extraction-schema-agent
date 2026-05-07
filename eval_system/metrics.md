# 定义

## 评测对象

对每篇文档，gold 和 prediction 都视为一个**无序的 Extraction 集合**

定义单个 extraction 为：
$$
E=(c,t,A)
$$
其中：

- c：`extraction_class`
- t：`extraction_text`
- A：`attributes` 字典



## 匹配

### 文本严格匹配

当且仅当归一化后的`label text`和`pred text`完全相同时，该pair被标记为文本严格匹配

形式上
$$
StrictTextMatch(t_{label}, t_{pred}) = 1 \iff N(t_{label}) = N(t_{pred})
$$
**示例**

```
label text = "Add metrics exposing controller throughput, latency etc."
pred text A = "Add metrics exposing controller throughput, latency etc."
pred text B = "Add metrics exposing controller throughput"
```

* StrictTextMatch(label, A) = 1

* StrictTextMatch(label, B) = 0



### 文本宽松匹配

将归一化后的`label text`和`pred text`使用tokenizer切成token序列`label tokenized text`$(T_l)$和`pred tokenized text`$(T_p)$后，计算token-level precision / recall / F1
$$
P = \frac{|T_l \cap T_p|}{|T_p|} \\
R = \frac{|T_l \cap T_p|}{|T_l|} \\
F1 = \frac{2PR}{P+R}
$$
当且仅当`label tokenized text`和`pred tokenized text`满足以下条件之一时，该pair被标记为文本宽松匹配

1. `pred text`是`label text`的一个连续子片段，且$R > \tau_R$
2. `label text`是`pred text`的一个连续子片段，且$P > \tau_P$
3. $F1 > \tau_{F1}$，且$\frac{LCCS(T_l, T_p)}{min(|T_l|,|T_p|)}>\tau_{LCCS}$

其中LCCS（ longest common contiguous subsequence）为最长公共连续 token 片段长度

形式上
$$
RelaxedTextMatch(t_{label}, t_{pred}) = 1 \\
\Updownarrow \\
(t_{pred} \sqsubseteq t_{label} \space \land \space R > \tau_R) \space \lor \space
(t_{label} \sqsubseteq t_{pred} \space \land \space P > \tau_P) \space \lor \space
(F1 > \tau_{F1} \space \land \space \frac{LCCS(T_l, T_p)}{min(|T_l|,|T_p|)}>\tau_{LCCS})
$$


**LCCS 示例**

```
label text = "→select test scenarios← that we believe are expected from all conforming clusters"
pred text = "We will →select test scenarios←"
LCCS = |[select, test, scenarios]| = 3
```



### 属性匹配

当且仅当`label attributes`和`pred attributes`的filed和value都完全相同时，该pair被标记为属性匹配



### 匹配算法

最大权二分图匹配，匈牙利算法



# 评价指标

## 主要指标

对整篇文档或全部语料，计算P，R，F1

### Precision

TP占预测集的比例
$$
P = \frac{N(TP)}{N(p)} \\
$$

### Recall

TP占标注集的比例
$$
R = \frac{N(TP)}{N(l)} \\
$$

### F1

$$
F1 = \frac{2PR}{P+R}
$$



### Detection Strict P/R/F1

`label extraction_text`和`pred extraction_text` 文本严格匹配时，该pair被标记为TP

pair权重：1

**用途：判断模型有没有把这段文本抽出来**



### Detection Relaxed P/R/F1

`label extraction_text`和`pred extraction_text` 文本宽松匹配时，该pair被标记为TP

pair合法条件：$RelaxedTextMatch(t_{label}, t_{pred}) = 1$

pair权重：$F1(t_{label}, t_{pred})$

**用途：判断模型是否至少抓到了大体正确的文本片段，即使边界略有漂移**



### Class Strict P/R/F1

`label`和`pred` 满足以下条件时，该pair被标记为TP

1. `extraction_class` 相同

2. `extraction_text`文本严格匹配

pair权重：1

**用途：判断模型是否抽到了正确文本且正确识别类别**



### Class Relaxed P/R/F1

`label`和`pred` 满足以下条件时，该pair被标记为TP

1. `extraction_class` 相同

2. `extraction_text`文本宽松匹配

pair权重：$F1(t_{label}, t_{pred})$

**用途：用于分离两类问题：**

- **类别本身错**
- **文本边界略漂但类别对**

**如果 `Class Relaxed` 明显高于 `Class Strict`，说明主要问题不在分类，而在 extraction_text 边界或最小 span 控制**



### Structured Strict P/R/F1

`label`和`pred` 满足以下条件时，该pair被标记为TP

1. `extraction_class` 相同

2. `extraction_text`文本严格匹配
3. `attributes`属性匹配

pair权重：1

**用途：最严格、最完整的核心指标，用于判断模型是否完整正确地抽取了一条结构化标注**



### Structured Relaxed P/R/F1

`label`和`pred` 满足以下条件时，，该pair被标记为TP

1. `extraction_class` 相同

2. `extraction_text`文本宽松匹配
3. `attributes`属性匹配

pair权重：$F1(t_{label}, t_{pred})$

**用途：判断模型是否在结构上基本正确，只存在轻微文本边界差异或轻微文本属性差异**



## grouding指标

`pred`中Extraction总数为N，grounding结果为MATCH_STATE的Extraction总数为m，则grounding率为$\frac{m}{N}$

其中MATCH_STATE有以下取值：

* MATCH_EXACT
* MATCH_LESSER
* MATCH_FUZZY
* MATCH_NONE

MATCH_STATE含义见抽取主链路说明文档



## 辅助指标

### Sructure Anomaly Rate

当一个Extraction满足以下条件之一时，被标记为结构异常：

1. `extraction_class` 不在 schema 中
2. `extraction_class` 合法，但 `attributes` 中出现非法字段
3. `extraction_class` 合法， `attributes` 合法，但`attributes`出现非法枚举值

`pred`中Extraction总数为N，结构异常Extraction数量为m，则
$$
Sructure Anomaly Rate = \frac{m}{N}
$$

### Error Buckets

包括以下Error Buckets

- `miss`：gold 没被召回。
- `spurious`：prediction 多抽了无对应项。
- `duplicate`：prediction 出现重复 extraction。
- `text_drift`：文本抓到了近似片段，但没有达到 class 级匹配。
- `class_error`：文本近似命中，但 class 错了。
- `attribute_error`：class 对了，但 attributes 错了。

