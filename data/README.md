# 数据目录说明

本目录用于存放省域经济综合竞争力评价项目的数据文件，包括原始数据、OCR 中间结果和清洗后的缓存结果。

## raw/nbs_exports

该目录存放从国家统计局数据平台下载的官方 CSV 文件。

程序会优先读取这里的文件，用于覆盖或补充 OCR 结果。当前主要使用的文件包括：

- `按照年份的GDP.csv`：各省地区生产总值，覆盖 2021-2024 年。
- `第一产业.csv`：各省第一产业增加值，覆盖 2021-2024 年。
- `第二产业.csv`：各省第二产业增加值，覆盖 2021-2024 年。
- `分省年度数据2024.csv`：2024 年 GDP、三次产业增加值、人均 GDP 等截面数据。
- `分省年度数据指数2024.csv`：2024 年地区生产总值指数，用于计算 GDP 增速。
- `分省年度数据消费指数.csv`：2024 年居民消费价格指数。
- `分省年度数据可支配收入.csv`：各省居民人均可支配收入，覆盖 2016-2024 年。
- `分省年度数据消费支出.csv`：各省居民人均消费支出，覆盖 2016-2024 年。

以下文件暂时作为辅助数据保留，后续如果扩展人口、城镇化或就业相关指标时可以使用：

- `分省年度数据人口.csv`
- `分省年度数据就业.csv`
- `分省年度数据出生率.csv`
- `2025GDP.csv`

## raw/yearbook_2023 和 raw/yearbook_2024

这两个目录存放从《中国统计年鉴》官网下载的 JPG 表格图片。

这些图片是 OCR 识别的原始来源，主要用于补充国家统计局 CSV 中没有直接下载到的指标，例如社会消费品零售总额、地方一般公共预算收入、固定资产投资增速等。

## raw/ocr_outputs

该目录存放 OCR 识别后的原始指标表。

主要文件包括：

- `province_indicators_2023.csv`
- `province_indicators_2023_metadata.csv`
- `province_indicators_2024.csv`
- `province_indicators_2024_metadata.csv`

这些文件还不是最终清洗结果，而是 OCR 和官方 CSV 合并之前或合并后的原始中间表。

## raw/archive

该目录存放早期下载、测试或已经被更完整文件替代的数据。

这些文件保留用于追溯数据来源和下载过程，但主程序不会直接依赖它们。

## data_cache

该目录存放最终清洗后的指标数据，是后续综合评价模型应该直接读取的数据。

主要交付文件包括：

- `indicators_2023.csv`
- `indicators_2023_metadata.csv`
- `indicators_2024.csv`
- `indicators_2024_metadata.csv`

其中 `indicators_YYYY.csv` 的行是 31 个省级行政区，列是经济指标；`metadata` 文件记录每个指标的中文含义、单位和说明。

## 对外数据接口

项目中统一的数据接口是：

```python
from src.data import get_indicators

df = get_indicators(2024)
```

该接口会返回指定年份的省域经济指标数据，当前数据表包含 31 个省份和 15 个指标。

## 数据质量检查

数据清洗质量检查接口是：

```python
from src.data import check_cached_indicators

report = check_cached_indicators(2024)
```

该接口会检查：

- 31 个省级行政区是否覆盖完整；
- 是否存在重复省份；
- 是否存在异常省份名称；
- 15 个指标列是否完整；
- 各列缺失值数量和缺失率。

年鉴图片下载和 OCR 解析的复现工具放在 `src/data/tools` 目录下：

- `download_yearbook_sources.py`
- `parse_yearbook_images.py`

当前 15 个指标包括：

- `gdp`：地区生产总值，单位为亿元。
- `gdp_growth`：GDP 增速，单位为 %。
- `primary_value`：第一产业增加值，单位为亿元。
- `secondary_value`：第二产业增加值，单位为亿元。
- `tertiary_value`：第三产业增加值，单位为亿元。
- `primary_share`：第一产业占 GDP 比重，单位为 %。
- `secondary_share`：第二产业占 GDP 比重，单位为 %。
- `tertiary_share`：第三产业占 GDP 比重，单位为 %。
- `retail`：社会消费品零售总额，单位为亿元。
- `income`：居民人均可支配收入，单位为元。
- `consumption_expenditure`：居民人均消费支出，单位为元。
- `cpi`：居民消费价格指数，单位为上年=100。
- `unemployment`：失业率代理指标，单位为 %。
- `fixed_invest`：固定资产投资增速，单位为 %。
- `fiscal_revenue`：地方一般公共预算收入，单位为亿元。
