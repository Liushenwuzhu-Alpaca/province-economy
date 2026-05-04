# 数据目录说明

本目录存放省域经济综合竞争力评价项目的原始数据、中间产物、分析结果和清洗缓存。

```
data/
├── raw/                  # 原始数据
│   ├── nbs_exports/      #   国家统计局导出的官方 CSV
│   ├── yearbook_2023/    #   2023 年统计年鉴 JPG 表格
│   ├── yearbook_2024/    #   2024 年统计年鉴 JPG 表格
│   ├── ocr_outputs/      #   OCR 识别后的原始指标表
│   └── archive/          #   早期下载/测试的历史文件
├── results/              # 分析结果缓存 (新增)
│   ├── 2024_pca/         #   2024 年 PCA 聚类结果
│   └── 2024_nopca/       #   2024 年无 PCA 聚类结果
└── ../data_cache/         # 清洗后的最终指标数据
    ├── indicators_2023.csv
    ├── indicators_2023_metadata.csv
    ├── indicators_2024.csv
    └── indicators_2024_metadata.csv
```

---

## 一、原始数据 (raw/)

### nbs_exports/

国家统计局官方导出 CSV。程序优先读取这里的文件，用于覆盖或补充 OCR 结果。

| 文件                              | 内容                       | 覆盖年份   |
| --------------------------------- | -------------------------- | ---------- |
| `按照年份的GDP.csv`                 | 各省地区生产总值             | 2021-2024  |
| `第一产业.csv`                     | 各省第一产业增加值           | 2021-2024  |
| `第二产业.csv`                     | 各省第二产业增加值           | 2021-2024  |
| `分省年度数据2024.csv`             | 2024 年 GDP + 三次产业 + 人均 | 2024       |
| `分省年度数据指数2024.csv`         | 2024 年地区生产总值指数      | 2024       |
| `分省年度数据消费指数.csv`          | 居民消费价格指数              | 2024       |
| `分省年度数据可支配收入.csv`        | 居民人均可支配收入            | 2016-2024  |
| `分省年度数据消费支出.csv`          | 居民人均消费支出              | 2016-2024  |
| `分省年度数据人口.csv`             | (辅助) 人口数据              | -          |
| `分省年度数据就业.csv`             | (辅助) 就业数据              | -          |
| `分省年度数据出生率.csv`           | (辅助) 出生率               | -          |
| `2025GDP.csv`                     | (辅助) 2025 年 GDP          | 2025       |

### yearbook_2023 / yearbook_2024

《中国统计年鉴》官网下载的 JPG 表格图片。OCR 识别后用于补充 CSV 中缺失的指标（消费零售总额、财政收支、固定资产投资、失业率等）。

### ocr_outputs/

OCR 识别后与官方 CSV 合并前的中间产物：

- `province_indicators_2023.csv` + `_metadata.csv`
- `province_indicators_2024.csv` + `_metadata.csv`

### archive/

早期下载/测试的文件，主流程不依赖。

---

## 二、分析结果缓存 (results/)

每次运行分析后，结果自动保存到 `data/results/{year}_{method}/`，包含：

| 文件           | 内容                                         |
| -------------- | -------------------------------------------- |
| `scores.csv`     | 熵权法评分排名 (province, score, rank)       |
| `clusters.csv`   | K-Means 聚类标签 (province, label)           |
| `weights.csv`    | 各指标熵权权重 (indicator, weight)           |
| `meta.json`      | 元信息 (silhouette, pca_var, 方法等)          |

二次运行默认加载缓存，跳过重复计算。使用 `--recompute` 强制重算。

---

## 三、对外数据接口

### 数据获取（给所有模块）

```python
from src.data import get_indicators

df = get_indicators(2024)       # 返回 31 省 × 15 指标的原始量纲 DataFrame
df = get_indicators(2023)
```

### 分析结果获取（给可视化模块）

可视化同学不需要直接操作原始数据，只需从缓存加载或调用分析接口：

```python
# 方式一: 从缓存加载 (推荐, 秒出)
from src.models.cache import load_results

result = load_results(2024, use_pca=True)  # 返回 dict

# 方式二: 从零分析 (首次或 --recompute)
from src.models.analyzer import analyze
from src.data import get_indicators

df = get_indicators(2024)
result = analyze(df)
```

分析结果字典结构（可视化直接消费）：

| 键            | 类型            | 形状           |
| ------------- | --------------- | -------------- |
| `scores`        | `pd.DataFrame`    | (31, 3)        |
| `clusters`      | `pd.DataFrame`    | (31, 2)        |
| `weights`       | `pd.Series`       | (10,)          |
| `pca_xy`        | `np.ndarray`      | (31, 2) 或 None |
| `pca_var`       | `list[float]`     | [2] 或 None     |
| `silhouette`    | `float`           | —               |
| `centers`       | `np.ndarray`      | (k, 2) 或 (k,m) |

---

## 四、指标对照

| 代码                        | 中文名称               | 单位     | 分析用? | 方向  |
| --------------------------- | ---------------------- | -------- | :-----: | :---: |
| `gdp`                         | 地区生产总值           | 亿元     | ✅       | 正向  |
| `gdp_growth`                  | GDP 增速                | %        | ✅       | 正向  |
| `retail`                      | 社会消费品零售总额     | 亿元     | ✅       | 正向  |
| `income`                      | 居民人均可支配收入     | 元       | ✅       | 正向  |
| `consumption_expenditure`     | 居民人均消费支出       | 元       | ✅       | 正向  |
| `tertiary_share`              | 第三产业占 GDP 比重     | %        | ✅       | 正向  |
| `fixed_invest`                | 固定资产投资增速       | %        | ✅       | 正向  |
| `fiscal_revenue`              | 地方一般公共预算收入   | 亿元     | ✅       | 正向  |
| `cpi`                         | 居民消费价格指数       | 上年=100 | ✅       | 负向* |
| `unemployment`                | 失业率代理指标         | %        | ✅       | 负向  |
| `primary_value`               | 第一产业增加值         | 亿元     | ❌       | —    |
| `secondary_value`             | 第二产业增加值         | 亿元     | ❌       | —    |
| `tertiary_value`              | 第三产业增加值         | 亿元     | ❌       | —    |
| `primary_share`               | 第一产业占 GDP 比重     | %        | ❌       | —    |
| `secondary_share`             | 第二产业占 GDP 比重     | %        | ❌       | —    |

> \* CPI 在分析中被转换为 |CPI - 100|（偏离稳定值越远越差）后作为负向指标处理。
>
> 指标选择逻辑和方向定义位于 `src/models/analyzer.py` 的 `ANALYSIS_INDICATORS` 和 `DIRECTIONS`。
