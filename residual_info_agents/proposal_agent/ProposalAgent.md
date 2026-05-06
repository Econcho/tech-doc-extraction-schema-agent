# 静态数据



## TriageSignal

Proposal 阶段用于向量召回和 bucket routing 的标准化信号对象。embedding_text=heading_tree + resblock_text + triage_reason

- signal_id: str

- doc_ref: str
- extraction_doc_ref: str | None

- block_id: int
- heading_tree

* text: str
* reason: str



## Bucket

外部维护的候选 proposal 聚合容器。
 它不是向量数据库内部对象，也不是 proposal 本体。

- bucket_id: str
- type: BucketType
- status: BucketStatus
- version: int
- member_signal_ids: list[str]
- support_doc_count: int
- support_signal_count: int
- lineage: BucketLineage | None

### BucketProposalType（enum）

- new_schema

- new_attr

### BucketStatus（enum）

- incubating
- stable
- stale
- ambiguous
- split
- merged
- archived
- rejected



## SignalBucketMapping

* signal_id: str
* bucket_id: str
* status: SignalBucketMappingStatus
* assigned_at: str



# 运行时数据



## SignalInfoRuntimeBlock

* doc_ref
* extraction_doc_ref
* resblock_id: str
* heading_tree: list[str]

* text: str

> 这里不加reason的原因是，reason本质上是TriageAgent对resinfo及其相关信息进行单次加工的结果，就产生reason的流程来说，ProposalAgent同样具备产生reason的能力。所以如果输入reason，本质上是输入一个<被加工过的已知信息>，干扰 > 作用



## WorkContext

* bucket_id: str
* signals: list[SignalInfoRuntimeBlock]



## LoopState

* context: WorkingContext
* turn_count
* transition_reason



# tools

## get_neighbor_text_of_resblocks

根据resblock_id对应的char_interval回查原文档，根据context_level确定该resblock对周围上下文的需求程度，为该resblock生成一个包含原文上下文的ContextBlock

### 输入

* doc_ref
* resblock_ids: list[int]
* context_levels: list[enum]
* ignore_code_fence: boolen

### 输出

list[ContextBlock]

## get_extraction_result_of_neighbor_text

根据resblock_id对应的resblock的char interval回查抽取结果json，根据context_level确定在抽取结果json中覆盖的char interval范围，获取char interval范围覆盖的所有Extraction结果

### 输入

* extraction_doc_ref
* resblock_ids: list[int]
* context_levels: list[enum]

### 输出

list[NeighborExtractions]

## get_original_text_from_heading_tree

根据resblock_id对应的heading_tree回查原文档，获取该heading_tree最后一级标题包含的所有内容。如果最后一级标题包含的内容还有下级标题，则只获取下级标题本身，不获取下级标题包含的内容

### 输入

* doc_ref
* resblock_ids: 
* ignore_code_fence: boolen

### 输出

list[FullHeadingContext]



# 存储workflow

![6c5c901556e43b22a2dde652f9f8b2f1](E:\xwechat_files\wxid_5jo8iy9nf1kq22_2cf2\temp\RWTemp\2026-04\6c5c901556e43b22a2dde652f9f8b2f1.jpg)

## embedding

### embedding模型选型

MVP 先选 `bge-m3`，因为它支持中英文和不同粒度文本，适合本地实验；如果走云服务，则用 `text-embedding-3-small` 做成本优先版本，用 `text-embedding-3-large` 做质量上限对照。最终通过 bucket route accuracy、bucket purity、proposal acceptance rate 做模型选择，而不是凭模型名拍板。

### embedding策略

source_index:
  heading_tree + resblock_text

reason_index:
  triage_reason

### 向量数据库选型

### rerank算法

RRF(signal) = Σ 1 / (c + rank_i)



## merge机制

### merge检查触发时机

如果bucket rank中$weight_{rank1} - weight_{rank2} < \alpha$，则触发对rank1 bucket和rank2 bucket的merge检查

### merge检查

当bucket A和bucket B满足以下条件时，标记为toBeMerged(A, B)

1. |A| > N 且 |B| > N
2. 在A中随机取m个向量$V_A = {v_1, v_2, ..., v_m}$，对每个$v \in V_A$，计算$v$在B中的TopK，满足$min(TopK)<\tau$
3. 在B中随机取m个向量$V_B = {v_1, v_2, ..., v_m}$，对每个$v \in V_B$，计算$v$在A中的TopK，满足$min(TopK)<\tau$

### merge流程

创建新bucket，signal为A+B。



## TopK→bucket rank

### 原则

1. 应使topk中有更多高相似度向量的桶排名更靠前
2. 在1的前提下，应使topk中有更多低相似度向量的桶排名更靠后
3. 如果一个桶a有极少量极高相似度向量，一个桶b有极多较高相似度向量，一种可能的情况是，极高相似度向量可能大部分是噪声匹配，而极多较高相似度大部分可能是正确匹配，基于这种情况，应该使b高于a

### bucket rank计算

已知：
$$
TopK=\{hit_i|hit_i = {signal\_id,bucket\_id,similarity,rank
}\}
$$
对某个 bucket `B`，取 topK 中所有属于它的 hits，记相似度为$s_i$
$$
H_B = \{hit_i | hit_i.bucket_{id} = B\}
$$
若$s_i > \tau_{high}$，则$hit_i$为高相似度支持项，其权重为
$$
weight_i=support_i = (s_i - τ_{high}) / (1 - τ_{high})
$$
若$s_i < \tau_{low}$，则$hit_i$为低相似度惩罚项，其权重为
$$
weight_i=penalty_i = -(τ_{low} - s_i) / τ_{low}
$$
若$\tau_{low} < s_i < \tau_{hight}$，则$hit_i$为弱支持项，其权重为
$$
weight_i = weak\_support_i= α \times (s_i - τ_{low}) / (τ_{high} - τ_{low})
$$
为了避免“极少数极高相似度向量”支配排名，需要引入有效支持数：
$$
N_{eff} = \frac{(\sum support_i + \sum weak\_support_i)^2}{\sum support_i^2 + \sum weak\_support_i^2 + ε}
$$


Bucket B的分数为
$$
score(B) = log(1 + N_{eff}) \times \sum{weight_i}
$$

# 架构overview

![proposal](F:\LLM\langextract-main\pics\proposal.svg)

# proposal workflow

## allow proposal 判断

### 判断时机

1. Bucket B每次append new signal时，对B进行判断
2. DB每新增N个signal，对没有任何新增signal的bucket进行判断

### 判断条件

Bucket B满足以下条件时，被判断为allow proposal

1. support_doc > M
2. |B| > N



# ProposalAgent workflow

### ProposalCheck-SubAgent

检查ProposalAgent的输出是否和现有schema存在边界冲突