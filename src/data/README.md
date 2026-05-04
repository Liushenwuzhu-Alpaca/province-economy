# 数据抓取与清洗模块说明

本目录是项目中的数据获取与清洗模块，主要负责将国家统计局和统计年鉴中的原始数据整理为后续模型可以直接使用的标准化指标表。

## 完成的主要工作

1. 搭建了统一的数据读取接口 `get_indicators(year)`。

   该接口会返回指定年份的省域经济指标数据，当前支持 2023 年和 2024 年，输出结果为 31 个省份和 15 个指标。

2. 整合了多种数据来源。

   当前数据来源包括国家统计局导出的官方 CSV、《中国统计年鉴》JPG 表格、OCR 识别结果和本地清洗缓存。

3. 实现了官方 CSV 数据读取。

   `nbs_exports.py` 用于读取 `data/raw/nbs_exports` 中的官方 CSV，并提取 GDP、产业增加值、收入、消费支出、CPI 等指标。

4. 实现了统计年鉴 JPG 抓取与 OCR 解析。

   `nbs_yearbook.py` 负责定位和下载统计年鉴表格图片，`yearbook_ocr.py` 负责从 JPG 表格中识别数据，并整理为省级指标表。

5. 实现了数据清洗。

   `cleaner.py` 负责统一省份名称、提取数值、检查 31 个省份是否齐全、处理缺失值，并输出数值型指标表。

6. 建立了缓存机制。

   清洗后的最终结果会写入 `data_cache/indicators_YYYY.csv`，避免每次运行都重新解析原始数据。

7. 整理了数据复现工具。

   `tools` 目录中保留了年鉴图片下载和 OCR 解析脚本，方便后续复现数据抓取过程。

## 对外接口

项目其他部分应该优先使用下面的接口获取数据：

```python
from src.data import get_indicators

df = get_indicators(2024)
```

返回结果：

- 行索引：`province`，表示省级行政区；
- 列：15 个经济指标；
- 类型：`pandas.DataFrame`。

## 当前指标

当前输出的 15 个指标包括：

- `gdp`：地区生产总值，亿元。
- `gdp_growth`：GDP 增速，%。
- `primary_value`：第一产业增加值，亿元。
- `secondary_value`：第二产业增加值，亿元。
- `tertiary_value`：第三产业增加值，亿元。
- `primary_share`：第一产业占 GDP 比重，%。
- `secondary_share`：第二产业占 GDP 比重，%。
- `tertiary_share`：第三产业占 GDP 比重，%。
- `retail`：社会消费品零售总额，亿元。
- `income`：居民人均可支配收入，元。
- `consumption_expenditure`：居民人均消费支出，元。
- `cpi`：居民消费价格指数，上年=100。
- `unemployment`：失业率代理指标，%。
- `fixed_invest`：固定资产投资增速，%。
- `fiscal_revenue`：地方一般公共预算收入，亿元。

## 文件说明

- `__init__.py`：导出数据模块的主要接口。
- `cleaner.py`：负责省份名称标准化、数值清洗、缺失值填补和最终字段检查。
- `fetcher.py`：负责统一调度数据读取、缓存读取、缓存刷新和元数据写入。
- `nbs_exports.py`：负责读取国家统计局导出的 CSV 文件。
- `nbs_yearbook.py`：负责查找和下载统计年鉴 JPG 表格。
- `yearbook_ocr.py`：负责 OCR 解析统计年鉴 JPG，并生成原始指标表。
- `tools/`：存放数据抓取和 OCR 解析的复现脚本。

## 运行示例

```bash
uv run python main.py
```

也可以直接在 Python 中调用：

```python
from src.data import get_indicators

df = get_indicators(2024)
print(df.head())
```

## 与指标清洗检查模块的关系

本目录主要完成数据获取和原始清洗。指标层面的质量检查放在 `src/indicators` 中，例如缺失值检查、省份覆盖检查、指标列完整性检查等。
