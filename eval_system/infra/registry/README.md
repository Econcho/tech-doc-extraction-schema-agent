# 注册系统说明

`eval_system/registry` 是评测系统中的注册层，位于“原始文档与标注文件”和“评测运行”之间。

它的职责是：
- 注册哪些文档需要参与某一个评测子集
- 将评测子集定义从目录扫描逻辑中解耦出来
- 为评测运行提供稳定、可控的文档清单

注册系统本身是通用的，不是 KEP 专用。  
KEP 只是当前接入注册系统的一类文档数据集。

## 1. 核心思想

注册系统将评测流程拆成三层：

1. 原始资产层
   存放文档和标注文件
2. 注册层
   用注册表文件定义“哪些文档属于哪个评测子集”
3. 评测运行层
   读取注册表，并只对注册表中列出的文档执行评测

这样做的好处是：
- 不需要靠扫描整个数据目录来决定评测集
- 一个评测子集就是一个独立注册表文件
- 不同子集之间天然解耦
- 后续可以扩展到其他类型文档，而不需要修改注册系统核心结构

## 2. 注册表文件格式

一个注册表文件是一个 JSON 文件，表示一个独立的评测子集。

示例：

```json
{
  "registry_name": "kep_all_labeled",
  "version": "v1",
  "domain": "kep",
  "schema_version": "kep_schema_v2",
  "entries": [
    {
      "doc_id": "19-Graduate-CronJob-to-Stable",
      "doc_type": "sig-apps",
      "document_path": "docs/sig-apps/19-Graduate-CronJob-to-Stable/README.md",
      "label_path": "labels/sig-apps/19-Graduate-CronJob-to-Stable/label_v2.json",
      "enabled": true,
      "metadata": {
        "label_filename": "label_v2.json",
        "document_filename": "README.md"
      }
    }
  ]
}
```

### 2.1 顶层字段

- `registry_name`
  注册表名称，用于标识一个评测子集

- `version`
  注册表版本号

- `domain`
  文档领域名称，例如 `kep`

- `schema_version`
  当前评测使用的 schema 版本

- `entries`
  注册条目列表

### 2.2 注册条目字段

每个 `entry` 表示一个参与评测的文档。

必填字段：
- `doc_id`
  文档唯一标识

- `doc_type`
  文档类型或所属分类

- `document_path`
  文档路径，相对于注册表文件所在目录

- `label_path`
  标注文件路径，相对于注册表文件所在目录

可选字段：
- `enabled`
  是否启用该条目。为 `false` 时，该条目默认不参与评测

- `metadata`
  扩展元信息，可存放任意附加字段

## 3. 注册系统目录说明

当前主要文件如下：

- [`models.py`](/F:/LLM/langextract-main/eval_system/registry/models.py)
  定义注册表与注册条目的数据模型

- [`loader.py`](/F:/LLM/langextract-main/eval_system/registry/loader.py)
  负责从 JSON 文件加载注册表

- [`service.py`](/F:/LLM/langextract-main/eval_system/registry/service.py)
  提供给评测运行使用的统一接口

- [`builder.py`](/F:/LLM/langextract-main/eval_system/registry/builder.py)
  提供从“文档目录 + 标注目录”自动构建注册表的通用工具

## 4. 运行时用法

### 4.1 读取注册表

```python
from eval_system.registry import RegistryService

service = RegistryService()
registry = service.load("eval_system/dataset/KEP/registry_all.json")
print(registry.registry_name)
```

### 4.2 获取启用的注册条目

```python
from eval_system.registry import RegistryService

service = RegistryService()
entries = service.list_entries(
    "eval_system/dataset/KEP/registry_all.json",
    enabled_only=True,
)
print([entry.doc_id for entry in entries])
```

### 4.3 解析文档路径和标注路径

```python
from eval_system.registry import RegistryService

service = RegistryService()
entries = service.list_entries("eval_system/dataset/KEP/registry_all.json")
document_path, label_path = service.resolve_entry_paths(
    "eval_system/dataset/KEP/registry_all.json",
    entries[0],
)
print(document_path)
print(label_path)
```

## 5. 在评测系统中使用注册表

`EvaluationRunner` 已支持通过注册表驱动加载数据集。

配置示例：

```yaml
dataset:
  registry_path: eval_system/dataset/KEP/registry_all.json
```

当配置中提供 `registry_path` 时，评测系统会：

1. 读取该注册表
2. 获取所有启用的注册条目
3. 加载每个条目对应的文档和标注
4. 将这些条目组成当前评测子集

此时不再依赖旧的 manifest/split 方式来决定评测集。

## 6. 如何生成注册表

[`FileSystemRegistryBuilder`](/F:/LLM/langextract-main/eval_system/registry/builder.py) 是一个通用构建器，适用于这种目录结构：

- 一个文档根目录
- 一个标注根目录

它可以配置：
- 文档目录名
- 标注目录名
- 文档文件名
- 标注文件优先级

示例：

```python
from eval_system.registry import FileSystemRegistryBuilder

builder = FileSystemRegistryBuilder()
builder.write_registry(
    dataset_root="eval_system/dataset/KEP",
    registry_path="eval_system/dataset/KEP/registry_all.json",
    registry_name="kep_all_labeled",
    domain="kep",
    schema_version="kep_schema_v2",
    docs_dir="docs",
    labels_dir="labels",
    document_filename="README.md",
    preferred_label_names=("label_v2_normalized.json", "label_v2.json"),
)
```

当前 KEP 数据集就是用这种方式组织的：
- `docs/` 存放原文档
- `labels/` 存放标注

但这个构建器并不限定只能用于 KEP。

## 7. 解耦原则

每个注册表文件都表示一个独立评测子集，例如：
- `registry_all.json`
- `registry_smoke.json`
- `registry_core.json`
- `registry_challenge.json`

这些注册表之间应当解耦，建议遵循以下原则：

1. 一个注册表只定义一个子集
2. 不依赖其他注册表进行继承或拼接
3. 子集边界应由注册表自身明确表达
4. 评测运行只读取当前指定的注册表

这样可以保证：
- 子集独立可复现
- 配置简单
- 后续维护成本低

## 8. 扩展建议

如果后续要接入其他类型文档，建议：

1. 保持注册表 JSON 结构不变
2. 针对新的数据组织方式新增发现/构建工具
3. 不要修改注册系统核心接口

也就是说：
- 注册系统的稳定契约是“注册表文件格式”
- 不同数据集可以有各自的构建逻辑

这样既能保持通用性，也能适应不同项目的数据组织方式。
