# 模型分析模块说明

本目录是项目中的模型分析模块，负责在标准化指标数据之上运行熵权法综合评分和 K-Means 聚类，并管理结果缓存和输出。

## 完成的主要工作

1. 实现了熵权法客观赋权与综合评分。

   `entropy.py` 根据指标的信息离散程度自动分配权重，无需主观判断，输出 31 省得分与排名。

2. 实现了 PCA 降维与 K-Means 聚类。

   `clustering.py` 用 PCA 去除指标共线性后聚类，将 31 省划分为四个发展梯队，支持跳过 PCA 直接聚类。

3. 搭建了数据到模型的桥接层。

   `analyzer.py` 负责指标选取、方向定义（正向/负向）、CPI 特殊处理、双归一化（Min-Max + Z-Score），统一调度两种方法并合并返回结果。

4. 建立了分析结果缓存机制。

   `cache.py` 将每次分析的结果（得分表、聚类标签、权重、元信息）写入 `data/results/`，二次运行直接加载缓存。

5. 实现了结果打印输出。

   `reporter.py` 统一格式化输出权重分布、TOP10 排名、梯队分布和聚类质量指标。

## 目录结构

```
src/models/
├── __init__.py       # 导出所有公开接口
├── entropy.py        # 方法A: 熵权法评分
├── clustering.py     # 方法B: PCA + K-Means 聚类
├── analyzer.py       # 桥接层: 归一化 + 调度
├── cache.py          # 结果缓存读写
└── reporter.py       # 结果打印
```

## 对外接口

### 完整分析（给 main.py 和可视化模块）

```python
from src.models.analyzer import analyze
from src.data import get_indicators

df = get_indicators(2024)
result = analyze(df, k=4, use_pca=True)
```

参数：

| 参数          | 默认值           | 说明                                          |
| ------------- | ---------------- | --------------------------------------------- |
| `raw_df`        | —                | `get_indicators()` 返回的原始指标 DataFrame     |
| `indicators`    | 内部预定义的 10 项 | 可按需传入指标子集                            |
| `k`             | 4                | 聚类数量                                      |
| `use_pca`       | True             | 是否先用 PCA 降维再聚类                        |

返回字典结构：

| 键            | 类型            | 说明                                                |
| ------------- | --------------- | --------------------------------------------------- |
| `scores`        | `pd.DataFrame`    | 方法A 输出: [province, score, rank]                   |
| `weights`       | `pd.Series`       | 熵权法各指标权重                                     |
| `clusters`      | `pd.DataFrame`    | 方法B 输出: [province, label] (0 = 最高梯队)         |
| `pca_xy`        | `np.ndarray` 或 None | 前 2 主成分坐标, 无 PCA 时为 None                |
| `pca_var`       | `list` 或 None    | 各主成分方差解释率, 无 PCA 时为 None                 |
| `silhouette`    | `float`           | 聚类 Silhouette 系数                                  |
| `centers`       | `np.ndarray`      | 簇中心坐标, PCA=(k,2) / 无PCA=(k,m)                  |

### 单独调用子方法

```python
# 熵权法 (需自行 Min-Max 归一化)
from src.models import entropy_weight
a = entropy_weight(normed_df)  # → {"scores": df, "weights": series}

# K-Means 聚类 (需自行 Z-Score 标准化)
from src.models import cluster_analysis
b = cluster_analysis(std_df, k=4, use_pca=True)  # → {"clusters": df, "pca_xy": arr, ...}
```

### 缓存读写

```python
from src.models.cache import load_results, save_results, cache_valid

if cache_valid(2024, use_pca=True):
    result = load_results(2024, use_pca=True)
# save_results() 由 analyze() 内部自动调用
```

### 打印结果

```python
from src.models.reporter import print_method_a, print_method_b

print_method_a(result)                # 权重 + 排名
print_method_b(result, use_pca=True)  # 聚类 + Silhouette
```

## 使用的分析指标

分析默认使用从 15 个全量指标中选取的 10 个核心指标。完整的指标选取逻辑和方向定义位于 `analyzer.py` 的 `ANALYSIS_INDICATORS` 和 `DIRECTIONS`，详见 `data/README.md` 第四部分。

## 运行示例

```bash
# 默认运行 (PCA + 缓存)
uv run python main.py

# 跳过 PCA
uv run python main.py --no-pca

# 强制重算
uv run python main.py --recompute

# 指定年份
uv run python main.py --year 2023
```

也可在 Python 中直接调用：

```python
from src.models.analyzer import analyze
from src.data import get_indicators

df = get_indicators(2024)
result = analyze(df)
print(result["scores"].head(10))
print(result["clusters"]["label"].value_counts())
```

## 与数据模块的关系

本模块依赖 `src.data.get_indicators()` 输出清洗后的原始指标表。数据层负责"拿什么数据"，模型层负责"怎么算"——两模块通过 `analyzer.py` 中的指标方向和归一化为边界，各层独立修改不影响对方。
